"""Production glue between MaigoKite product semantics and LangGraph.

LangChain owns the agent loop and tool orchestration.  This module owns only
runtime invocation, stable MaigoKite event projection, approval bridging, and
product persistence projection.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    TodoListMiddleware,
)
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain.agents.middleware.types import ModelRequest, ModelResponse, ToolCallRequest
from langchain_anthropic import ChatAnthropic
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages import ToolCall as NativeToolCall
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.errors import GraphInterrupt
from langgraph.types import Command, interrupt

from agent.models.reasoning import visible_reasoning
from agent.repository import ConversationBusyError, SQLiteRepository
from agent.runtime.context import ContextBudgetMiddleware, SafeSummarizationMiddleware
from agent.runtime.subagents import CHILD_TAG, ChildContext, DelegateTool, ListSubagentModelsTool, create_readonly_agent
from agent.tools.base import BaseTool
from agent.tools.native.file_read import FileReadTool
from agent.tools.native.file_write import FileWriteTool
from agent.tools.permission_mgr import PermissionManager, PolicyDecision, RiskLevel
from agent.tools.validator import ToolValidator, ValidationError


@dataclass(frozen=True, slots=True)
class MaigoKiteEvent:
    """A stable product event that does not expose LangGraph event classes."""

    type: str
    payload: dict[str, Any]


EventPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]
ModelResolver = Callable[[str, str, str], Awaitable[tuple[str, BaseChatModel]]]


@dataclass(frozen=True, slots=True)
class RuntimeRunRequest:
    workspace_id: str = "personal"
    conversation_id: str = ""
    task_id: str = ""
    principal_id: str = "local-user"
    permission_mode: str = "read_only"
    trace_id: str = ""
    request_hash: str = ""


@dataclass(frozen=True, slots=True)
class ProductToolSpec:
    """The only bridge needed for a migrated MaigoKite tool."""

    tool: BaseTool
    runtime_tool: StructuredTool


_END = object()


class RunHandle:
    """One run owns one root asyncio task and an event queue."""

    def __init__(
        self,
        request: RuntimeRunRequest,
        root_task: asyncio.Task[None],
        queue: asyncio.Queue[MaigoKiteEvent | object],
        started: asyncio.Event,
    ) -> None:
        self.request = request
        self.root_task = root_task
        self._queue = queue
        self._started = started

    async def events(self) -> AsyncIterator[MaigoKiteEvent]:
        while True:
            item = await self._queue.get()
            if item is _END:
                return
            assert isinstance(item, MaigoKiteEvent)
            yield item

    async def collect(self) -> list[MaigoKiteEvent]:
        return [event async for event in self.events()]

    async def wait(self) -> None:
        await asyncio.shield(self.root_task)

    async def cancel(self) -> None:
        # Let the root enter its try/finally before cancellation. Otherwise an
        # immediate stop can prevent all cleanup/status/queue-finalization code
        # from running. The root yields at this barrier before doing any work.
        if not self.root_task.done():
            await self._started.wait()
        if not self.root_task.done() and not self.root_task.cancelling():
            self.root_task.cancel()
        try:
            # Repeated stop/shutdown callers must not interrupt root cleanup.
            await asyncio.shield(self.root_task)
        except asyncio.CancelledError:
            if not self.root_task.done():
                raise


@dataclass(slots=True)
class _RunContext:
    adapter: "LangGraphRuntime"
    request: RuntimeRunRequest
    queue: asyncio.Queue[MaigoKiteEvent | object]
    execution_metadata: dict[str, Any] = field(default_factory=dict)
    tool_calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    latest_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finished_tool_calls: set[str] = field(default_factory=set)
    terminal_emitted: bool = False
    reasoning_parts: list[str] = field(default_factory=list)
    reasoning_started: bool = False
    reasoning_completed: bool = False
    reasoning_streamed: bool = False
    final_saved: bool = False
    interrupted: bool = False
    tool_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    event_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    started: asyncio.Event = field(default_factory=asyncio.Event)
    direct_tool: NativeToolCall | None = None
    review_call_ids: set[str] = field(default_factory=set)
    boundary_review_ids: set[str] = field(default_factory=set)
    authorizations: list[dict[str, Any]] = field(default_factory=list)
    max_subagent_calls: int = 0
    subagent_model_ids: list[str] = field(default_factory=list)
    child_slots: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(1))
    child_scope: asyncio.TaskGroup | None = None


class _ProductToolMiddleware(AgentMiddleware):
    """Map official tool execution callbacks to MaigoKite product concerns."""

    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        context = runtime.context
        pending = await context.adapter.repository.task_inputs(
            context.request.workspace_id, context.request.task_id, pending=True,
        )
        known = {message.id for message in state["messages"]}
        messages = [HumanMessage(content=item["content"], id=item["id"])
                    for item in pending if item["id"] not in known]
        return {"messages": messages} if messages else None

    async def aafter_model(self, state: Any, runtime: Any) -> None:
        # after_model hooks run in reverse order: refresh before native HITL,
        # including permission changes made while the provider was streaming.
        await runtime.context.adapter._refresh_execution_metadata(runtime.context)

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        context = request.runtime.context
        if context.direct_tool is not None:
            # /tool is explicit user intent, not a second execution engine.
            # Native model-node output still passes through HITL and ToolNode.
            last = request.messages[-1]
            if isinstance(last, HumanMessage):
                return ModelResponse(result=[AIMessage(content="", tool_calls=[context.direct_tool])])
            if isinstance(last, ToolMessage):
                artifact = last.artifact if isinstance(last.artifact, dict) else {}
                content = artifact.get("raw") or artifact.get("summary") or last.text
                return ModelResponse(result=[AIMessage(content=str(content))])
            raise RuntimeError("direct tool command has no matching tool result")
        enabled = request.runtime.context.execution_metadata.get("enabled_tools")
        if enabled is not None:
            request = request.override(tools=[tool for tool in request.tools
                                             if getattr(tool, "name", "") in {*enabled, "write_todos"}])
        if context.max_subagent_calls == 0:
            request = request.override(tools=[tool for tool in request.tools if getattr(tool, "name", "") not in {"delegate", "list_subagent_models"}])
        response = await handler(request)
        # A budget rejection or failed/cancelled request is not a confirmed
        # consumption receipt. A successful model response confirms this input;
        # remote consumption after a lost response remains deliberately unknown.
        consumed = await context.adapter.repository.consume_task_inputs(
            context.request.workspace_id, context.request.task_id,
            {str(message.id) for message in request.messages if isinstance(message, HumanMessage)},
        )
        for item in consumed:
            await context.adapter._emit(context, "task.input.consumed", {
                "input_id": item["id"], "content": item["content"], "status": "consumed",
            })
        return response

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        context = request.runtime.context
        if not isinstance(context, _RunContext):
            raise RuntimeError("LangGraph runtime context is missing")
        if request.tool_call["name"] == "delegate":
            # ToolNode fans out independent investigations. Their own semaphore
            # limits concurrency; holding the file-mutation lock here would
            # silently turn every user's parallel setting into one.
            if context.child_scope is None or context.terminal_emitted:
                raise RuntimeError("delegation requires an active root task scope")
            work = context.child_scope.create_task(
                context.adapter._execute_product_tool_call(request, handler),
                name=f"delegate:{request.tool_call['id']}",
            )
            return await work
        # ToolNode retains orchestration and results. Serialize tool bodies
        # during migration, including writes to the same file in one batch.
        async with context.tool_lock:
            if request.tool_call["name"] == "write_todos":
                # Framework-owned planning state, not a filesystem/workspace
                # TODO mutation. ToolNode owns the returned Command update.
                await context.adapter.repository.update_tool_call(request.tool_call["id"], "running")
                await context.adapter._emit(context, "tool.started", {
                    "tool_call_id": request.tool_call["id"], "tool_name": "write_todos",
                    "arguments": request.tool_call.get("args", {}),
                })
                return await handler(request)
            return await context.adapter._execute_product_tool_call(request, handler)


class LangGraphRuntime:
    """Thin production adapter using framework loop, persistence, and HITL."""

    def __init__(
        self,
        *,
        model: BaseChatModel | None = None,
        model_resolver: ModelResolver | None = None,
        model_catalog: Callable[[str], Awaitable[list[dict[str, Any]]]] | None = None,
        workspace_root: str | Path,
        checkpoint_path: str | Path,
        product_db_path: str | Path | None = None,
        repository: SQLiteRepository | None = None,
        policy: PermissionManager | None = None,
        event_publisher: EventPublisher | None = None,
        tools: Sequence[ProductToolSpec] | None = None,
        system_prompt: str = "",
        context_max_tokens: int = 32000,
        max_model_calls: int = 8,
        execution_metadata: Callable[[RuntimeRunRequest], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        if model is None and model_resolver is None:
            raise ValueError("model or model_resolver is required")
        if repository is None and product_db_path is None:
            raise ValueError("product_db_path is required when repository is not provided")
        self.model = model
        if context_max_tokens <= 0 or max_model_calls <= 0:
            raise ValueError("context_max_tokens and max_model_calls must be positive")
        self.system_prompt = system_prompt
        self.context_max_tokens = context_max_tokens
        self.max_model_calls = max_model_calls
        self.model_resolver = model_resolver
        self.model_catalog = model_catalog
        self._execution_metadata = execution_metadata
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.checkpoint_path = (
            Path(checkpoint_path).expanduser().resolve()
            if str(checkpoint_path) != ":memory:"
            else Path(":memory:")
        )
        if repository is None:
            assert product_db_path is not None
            self.repository = SQLiteRepository(product_db_path)
        else:
            self.repository = repository
        self._owns_repository = repository is None
        self.policy = policy or PermissionManager("read_only", self.workspace_root)
        self._event_publisher = event_publisher
        if tools is None:
            read_tool = FileReadTool()
            write_tool = FileWriteTool()
            self.tool_specs = [
                ProductToolSpec(read_tool, read_tool.to_langchain_tool()),
                ProductToolSpec(write_tool, write_tool.to_langchain_tool()),
            ]
        else:
            self.tool_specs = list(tools)
        # Tool order is part of the provider's reusable prompt prefix.
        self.tool_specs.sort(key=lambda spec: spec.tool.name)
        self._specs_by_name = {spec.tool.name: spec for spec in self.tool_specs}
        self._validator = ToolValidator(
            lambda name: self._specs_by_name[name].tool.parameters_schema
            if name in self._specs_by_name else None
        )
        self._checkpointer_context: Any | None = None
        self._checkpointer: AsyncSqliteSaver | None = None
        self._graphs: dict[str, Any] = {}
        self._readonly_graphs: dict[str, Any] = {}
        self._active_runs: dict[str, RunHandle] = {}
        self._conversation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._checkpoint_threads: set[str] = set()
        self._opened = False

    async def open(self) -> None:
        if self._opened:
            return
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        if str(self.checkpoint_path) != ":memory:":
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        if self._owns_repository:
            await self.repository.open()
        self._checkpointer_context = AsyncSqliteSaver.from_conn_string(
            str(self.checkpoint_path)
        )
        self._checkpointer = await self._checkpointer_context.__aenter__()
        self._opened = True
        if self.model is not None:
            self._graphs["fixed"] = self._create_graph(self.model)

    def readonly_graph(self, key: str, model: BaseChatModel) -> Any:
        """Cache compiled native child graphs, not execution state or HTTP clients."""
        if key not in self._readonly_graphs:
            self._readonly_graphs[key] = create_readonly_agent(model, self.tool_specs, self.context_max_tokens, self.max_model_calls)
        return self._readonly_graphs[key]

    def _create_graph(self, model: BaseChatModel, model_info: dict[str, Any] | None = None) -> Any:
        child = create_readonly_agent(model, self.tool_specs, self.context_max_tokens, self.max_model_calls)
        info = {**(model_info or {}), "model": getattr(model, "model_name", None) or getattr(model, "model", "")}
        runtime_tools = [DelegateTool(child, info).to_langchain_tool() if spec.tool.name == "delegate"
                         else ListSubagentModelsTool(info).to_langchain_tool() if spec.tool.name == "list_subagent_models"
                         else spec.runtime_tool for spec in self.tool_specs]
        interrupt_on: dict[str, bool | InterruptOnConfig] = {
            spec.tool.name: InterruptOnConfig(
                allowed_decisions=["approve", "reject"],
                when=self._should_interrupt,
                description=cast(Any, self._approval_description),
            )
            for spec in self.tool_specs
        }
        planning = TodoListMiddleware()
        middleware: list[AgentMiddleware[Any, Any, Any]] = [
            planning,
            ModelCallLimitMiddleware(thread_limit=self.max_model_calls, exit_behavior="error"),
            SafeSummarizationMiddleware(
                model=model,
                input_budget=self.context_max_tokens,
                system_prompt="\n\n".join(part for part in (self.system_prompt, planning.system_prompt) if part),
                tools=[*runtime_tools, *planning.tools],
            ),
            # Append queued user input after compaction so it cannot be reduced
            # to a summary before its first consumption receipt.
            HumanInTheLoopMiddleware(interrupt_on),
            _ProductToolMiddleware(),
            ContextBudgetMiddleware(self.context_max_tokens),
        ]
        if isinstance(model, ChatAnthropic):
            middleware.append(AnthropicPromptCachingMiddleware())
        return create_agent(
            model,
            runtime_tools,
            system_prompt=self.system_prompt or None,
            middleware=middleware,
            checkpointer=self._checkpointer,
            context_schema=_RunContext,
            name="maigokite-langgraph-runtime",
        )

    async def cancel_active_runs(self) -> None:
        """Stop the current roots using the same cancellation path as one run."""
        # A finished root may still be waiting for its release callback. Its
        # failure belongs to wait(), not a fresh cancellation request; replaying
        # that exception here would prevent closing already-idle resources.
        handles = [handle for handle in self._active_runs.values() if not handle.root_task.done()]
        if handles:
            results = await asyncio.gather(*(handle.cancel() for handle in handles), return_exceptions=True)
            # Finish draining every root even if one cleanup fails. Do not
            # silently report successful shutdown after a cleanup error.
            for result in results:
                if isinstance(result, BaseException):
                    raise result

    async def close(self) -> None:
        self._opened = False  # No new admissions while owned runs drain.
        errors: list[Exception] = []
        try:
            await self.cancel_active_runs()
        except Exception as exc:
            # cancel_active_runs waits for every root before reporting errors.
            errors.append(exc)
        self._active_runs.clear()
        self._conversation_locks.clear()
        self._graphs.clear()
        self._readonly_graphs.clear()
        await asyncio.sleep(0)
        if self._checkpointer is not None:
            for task_id in self._checkpoint_threads:
                try:
                    await self._checkpointer.aget_tuple(
                        {"configurable": {"thread_id": task_id}}
                    )
                except Exception as exc:
                    errors.append(exc)
        self._checkpoint_threads.clear()
        self._checkpointer = None
        if self._checkpointer_context is not None:
            try:
                await self._checkpointer_context.__aexit__(None, None, None)
            except Exception as exc:
                errors.append(exc)
            else:
                self._checkpointer_context = None
        if self._owns_repository:
            try:
                await self.repository.close()
            except Exception as exc:
                errors.append(exc)
        self._opened = False
        if errors:
            raise ExceptionGroup("Runtime cleanup failed after draining runs", errors)

    async def __aenter__(self) -> "LangGraphRuntime":
        await self.open()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    def _require_open(self) -> Any:
        if not self._opened or self._checkpointer is None:
            raise RuntimeError("LangGraph runtime is not open")
        return self._checkpointer

    async def _graph_for(self, request: RuntimeRunRequest) -> Any:
        self._require_open()
        if self.model is not None:
            return self._graphs["fixed"]
        assert self.model_resolver is not None
        conversation = await self.repository.get_conversation(
            request.workspace_id, request.conversation_id
        )
        key, model = await self.model_resolver(
            request.workspace_id, str(conversation.get("model_id") or ""),
            str(conversation.get("response_mode") or "balanced"),
        )
        self._require_open()
        graph = self._graphs.get(key)
        if graph is None:
            catalog = await self.model_catalog(request.workspace_id) if self.model_catalog else []
            info = next((item for item in catalog if item["model_id"] == conversation.get("model_id")), {})
            if not conversation.get("model_id"):
                info = next((item for item in catalog if item.get("is_default")), {})
            graph = self._create_graph(model, info)
            self._graphs[key] = graph
        return graph

    def _policy_decision(
        self, name: str, arguments: dict[str, Any], context: _RunContext | ChildContext, *, approved: bool = False,
    ) -> PolicyDecision:
        spec = self._specs_by_name.get(name)
        enabled = context.execution_metadata.get("enabled_tools", self._specs_by_name)
        if spec is None or name not in enabled:
            return PolicyDecision("deny", RiskLevel.L5, "tool is not enabled for this run", arguments)
        try:
            clean = self._validator.sanitize(name, arguments)
        except ValidationError as exc:
            return PolicyDecision("deny", RiskLevel.L5, str(exc), arguments)
        if name == "web_search" and not clean.get("engine"):
            keys = context.execution_metadata.get("api_keys", {})
            clean["engine"] = "tavily" if keys.get("tavily") else "google" if keys.get("google") else "duckduckgo"
        policy = self.policy.for_workspace(context.execution_metadata.get("workspace_root", self.workspace_root))
        decision = policy.evaluate(
            name,
            clean,
            approved=approved,
            risk_override=getattr(spec.tool, "risk_level", None),
            mode=context.execution_metadata.get("permission_mode", context.request.permission_mode),
        )
        # Only the parent can use its own explicitly scoped receipts. Child
        # tools never inherit authorizations, even inside the same conversation.
        if isinstance(context, _RunContext) and decision.outcome == "approval_required" and decision.reuse_scope:
            receipt = next((item for item in context.authorizations if item["resource"] == decision.reuse_scope), None)
            if receipt is not None:
                return replace(decision, outcome="allow", reason="allowed by scoped approval",
                               authorization_id=receipt["approval_id"])
        return decision

    async def _refresh_execution_metadata(self, context: _RunContext) -> None:
        context.authorizations = await self.repository.list_authorizations(
            context.request.workspace_id, context.request.conversation_id,
            context.request.principal_id, context.request.task_id,
        )
        if self._execution_metadata is None:
            return
        fresh = await self._execution_metadata(context.request)
        original = context.execution_metadata.get("enabled_tools", self._specs_by_name)
        # Tool discovery stays stable for this run; revocations still apply.
        fresh["enabled_tools"] = sorted(set(original) & set(fresh.get("enabled_tools", original)))
        fresh["permission_mode"] = self.policy.normalize_mode(
            str(fresh.get("permission_mode", context.request.permission_mode)),
        )
        # Replace rather than mutate: an already-started tool keeps its snapshot.
        context.execution_metadata = fresh

    def _should_interrupt(self, tool_request: Any) -> bool:
        context = tool_request.runtime.context
        if context.review_call_ids and any(
            call["id"] in context.review_call_ids for call in context.latest_tool_calls
        ):
            # Replay must consume the original native HITL batch. Newly gated
            # calls are checked separately at their actual execution boundary.
            return tool_request.tool_call["id"] in context.review_call_ids
        decision = self._policy_decision(
            str(tool_request.tool_call["name"]),
            dict(tool_request.tool_call.get("args") or {}),
            context,
        )
        return decision.outcome == "approval_required"

    def _approval_description(self, tool_call: dict[str, Any], _state: Any, runtime: Any) -> str:
        decision = self._policy_decision(
            str(tool_call["name"]),
            dict(tool_call.get("args") or {}),
            runtime.context,
        )
        return (
            f"{decision.reason}\n"
            f"Risk: {decision.risk.name}\n"
            f"Scope: {decision.resource_scope}"
        )

    async def start(
        self,
        prompt: str,
        request: RuntimeRunRequest | None = None,
    ) -> RunHandle:
        self._require_open()
        requested = request or RuntimeRunRequest()
        await self.repository.ensure_workspace(
            requested.workspace_id,
            requested.workspace_id,
            "personal" if requested.workspace_id == "personal" else "team",
        )
        if requested.conversation_id:
            conversation = await self.repository.get_conversation(
                requested.workspace_id, requested.conversation_id
            )
        else:
            conversation = await self.repository.create_conversation(
                requested.workspace_id,
                title=prompt[:80],
                permission_mode=requested.permission_mode,
            )
        task_id = requested.task_id or f"task_{uuid.uuid4().hex}"
        actual = replace(
            requested,
            conversation_id=str(conversation["id"]),
            task_id=task_id,
        )
        async with self._conversation_locks[actual.conversation_id]:
            return await self._start_turn(prompt, actual)

    def has_active_conversation(self, conversation_id: str) -> bool:
        return any(
            handle.request.conversation_id == conversation_id and not handle.root_task.done()
            for handle in self._active_runs.values()
        )

    async def delete_threads(self, task_ids: Sequence[str]) -> None:
        """Use the checkpointer's public deletion API, not custom checkpoint SQL."""
        if self._checkpointer is not None:
            for task_id in task_ids:
                await self._checkpointer.adelete_thread(task_id)
                self._checkpoint_threads.discard(task_id)

    async def _start_turn(self, prompt: str, actual: RuntimeRunRequest) -> RunHandle:
        await self.repository.check_message_replay(actual.workspace_id, actual.task_id, actual.request_hash)
        previous = await self.repository.latest_conversation_task(actual.workspace_id, actual.conversation_id)
        if previous and previous["status"] in {"created", "queued", "running", "waiting_approval", "retry_wait"}:
            raise ConversationBusyError("conversation has unfinished work; finish or cancel it before sending another turn")
        if self.has_active_conversation(actual.conversation_id):
            raise ConversationBusyError("conversation is still finishing its previous run")
        # Resolve credentials/model before committing product state. Failure to
        # prepare a run must not leave a phantom running task behind.
        graph = await self._graph_for(actual)
        self._direct_tool_call(prompt, actual.task_id)  # Validate command syntax before persisting.
        messages: list[Any] = []
        history_source = "product_history"
        if previous and previous["status"] == "succeeded":
            snapshot = await graph.aget_state({"configurable": {"thread_id": str(previous["id"])}})
            if snapshot.values and not snapshot.next and not snapshot.interrupts:
                # Carry the framework's retained messages, including its summary
                # and ToolMessages. Counters/interrupts belong to the old run.
                messages = list(snapshot.values.get("messages", []))
                history_source = "checkpoint"
        if not messages:
            # First migration/legacy or interrupted history: no invented tool
            # results or continuation. Import only the visible product history.
            history = await self.repository.list_messages(actual.conversation_id)
            messages = [
                {"role": str(item["role"]), "content": str(item["content"])}
                for item in history if str(item.get("role")) in {"user", "assistant", "system"}
            ]
            if previous and previous["status"] != "succeeded":
                # Retain this safety instruction in checkpoint history. The
                # model-call boundary merges it with create_agent's prompt into
                # one leading system message, including on subsequent turns.
                messages.insert(0, SystemMessage(
                    "Execution boundary: the previous task ended with status " + str(previous["status"]) +
                    ". Only visible conversation history was imported, not a runnable continuation. "
                    "Earlier tool side effects may have occurred. Inspect the actual state before repeating actions; "
                    "this note does not grant permission or imply a rollback."
                ))
        await self.repository.start_chat_turn(
            actual.task_id, actual.workspace_id, actual.conversation_id, prompt, actual.request_hash,
            model_call_limit=self.max_model_calls,
        )
        messages.append({"role": "user", "content": prompt})
        try:
            return await self._launch(
                {"messages": messages},
                actual,
                graph=graph,
                initial_events=[
                    ("task.started", {"trace_id": actual.trace_id, "input_text": prompt}),
                    ("context.history", {"source": history_source, "previous_task_id": previous["id"] if previous else None,
                                         "execution_resumed": False}),
                ],
            )
        except asyncio.CancelledError:
            # No root task owns this admission yet. Drain this entry before Core
            # closes Repository; do not leave a phantom running task until restart.
            await self.repository.cancel_task(actual.workspace_id, actual.task_id)
            await self._publish_event(actual, "task.cancelled", {"message": "cancelled before execution started"})
            raise
        except Exception as exc:
            task = await self.repository.get_task(actual.workspace_id, actual.task_id)
            if task["status"] != "cancelled":
                await self.repository.update_task_status(actual.task_id, "failed", str(exc))
                await self._publish_event(actual, "task.failed", {"message": str(exc), "error_type": type(exc).__name__})
            raise

    async def resume_approval(
        self,
        workspace_id: str,
        approval_id: str,
        principal_id: str,
        decision: str,
        version: int,
        note: str = "",
        scope: str = "once",
    ) -> RunHandle:
        self._require_open()
        pending = await self.repository.get_approval(workspace_id, approval_id)
        async with self._conversation_locks[str(pending["conversation_id"])]:
            handle = self._active_runs.get(str(pending["task_id"]))
            if handle is not None:
                # The interrupt may already be visible while its previous root
                # task is finishing. Await it before consuming a new decision.
                await asyncio.shield(handle.wait())
            return await self._resume_approval(workspace_id, approval_id, principal_id, decision, version, note, scope)

    async def _resume_approval(
        self, workspace_id: str, approval_id: str, principal_id: str, decision: str, version: int,
        note: str = "",
        scope: str = "once",
    ) -> RunHandle:
        if decision not in {"allow", "deny"}:
            raise ValueError("decision must be allow or deny")
        if scope not in {"once", "task", "session"} or (decision == "deny" and scope != "once"):
            raise ValueError("invalid approval scope")
        pending = await self.repository.get_approval(workspace_id, approval_id)
        pending_task = await self.repository.get_task(workspace_id, str(pending["task_id"]))
        conversation = await self.repository.get_conversation(
            workspace_id, str(pending_task["conversation_id"])
        )
        request = RuntimeRunRequest(
            workspace_id=workspace_id,
            conversation_id=str(pending_task["conversation_id"]),
            task_id=str(pending_task["id"]),
            principal_id=principal_id,
            permission_mode=str(conversation["permission_mode"]),
        )
        # Allow may resume execution and needs a model. Deny cancels the turn;
        # it must not depend on credentials or provider availability.
        graph = None
        if decision != "deny":
            graph = await self._graph_for(request)
            snapshot = await graph.aget_state({"configurable": {"thread_id": str(pending_task["id"])}})
            proposal = next((message for message in reversed(snapshot.values.get("messages", []))
                             if isinstance(message, AIMessage)), None)
            if not snapshot.interrupts or proposal is None:
                raise ValueError("approval has no matching runtime interrupt; cancel and start a new task")
            try:
                calls = self._review_calls(snapshot.interrupts, [dict(call) for call in proposal.tool_calls])
            except RuntimeError as exc:
                raise ValueError("approval no longer matches the runtime checkpoint") from exc
            call = next((call for call in calls if call["id"] == pending["tool_call_id"]
                         and call["name"] == pending["tool_name"]), None)
            if call is None:
                raise ValueError("approval no longer matches the runtime checkpoint")
            review_context = _RunContext(self, request, asyncio.Queue())
            if self._execution_metadata is not None:
                review_context.execution_metadata = await self._execution_metadata(request)
            policy = self._policy_decision(call["name"], call["args"], review_context)
            if policy.outcome == "deny" or not self._matches_approval(pending, call["name"], policy):
                # Do not consume the user's version for a different normalized
                # path/payload, even if the checkpoint reused the same call ID.
                raise PermissionError("approval parameters or policy changed; cancel and start a new task")
            if scope != "once" and (not policy.reuse_scope or policy.reuse_scope != pending.get("reuse_scope")):
                raise PermissionError("this approval has no matching reusable scope; use one-time approval")
        approval = await self.repository.decide_approval(
            workspace_id, approval_id, principal_id, decision, version, note, scope
        )
        if decision == "allow":
            # Approval consumption is not execution. The tool still waits for
            # the rest of the native HITL batch to be reviewed.
            await self.repository.update_tool_call(
                str(approval["tool_call_id"]), "waiting_approval"
            )
        return await self._launch(
            # Repository stores the user's decision, not execution state.
            # _drive resumes the native HITL batch only when review is complete.
            None,
            request,
            graph=graph,
            initial_events=[
                (
                    "approval.decided",
                    {
                        **self._approval_payload(approval),
                        "decision": decision,
                    },
                )
            ],
        )

    async def recover(
        self, workspace_id: str, task_id: str, *,
        principal_id: str = "local-user", version: int | None = None, trace_id: str = "",
    ) -> RunHandle:
        """Continue the latest checkpoint without inventing a continuation payload."""
        self._require_open()
        # The public entry requires an optimistic version and an explicit owner.
        # Unversioned recovery remains internal to the existing runtime spike.
        if version is not None:
            if await self.repository.check_workspace_access(workspace_id, principal_id) != "owner":
                raise PermissionError("only the workspace owner can resume interrupted execution")
            if version < 1:
                raise ValueError("a positive task version is required")
        task = await self.repository.get_task(workspace_id, task_id)
        conversation = await self.repository.get_conversation(
            workspace_id, str(task["conversation_id"])
        )
        request = RuntimeRunRequest(
            workspace_id=workspace_id,
            conversation_id=str(task["conversation_id"]),
            task_id=task_id,
            principal_id=principal_id,
            permission_mode=str(conversation["permission_mode"]),
            trace_id=trace_id,
        )
        async with self._conversation_locks[request.conversation_id]:
            task = await self.repository.get_task(workspace_id, task_id)
            if task["status"] in {"cancelled", "succeeded", "failed", "expired", "timed_out", "rejected"}:
                raise ValueError("terminal tasks cannot be replayed; send a new message")
            if version is not None and (task["status"] != "interrupted" or task["version"] != version):
                raise ValueError("task is not interrupted at this version; refresh its status")
            latest = await self.repository.latest_conversation_task(workspace_id, request.conversation_id)
            if latest and latest["id"] != task_id:
                raise ValueError("cannot recover an older turn after a newer turn was admitted")
            if self.has_active_conversation(request.conversation_id):
                raise ConversationBusyError("conversation still has an active run")
            if not await self.has_checkpoint(task_id):
                raise ValueError("no execution checkpoint is available for this task")
            graph = await self._graph_for(request)
            if version is not None:
                conversation = await self.repository.get_conversation(workspace_id, request.conversation_id)
                if conversation.get("archived"):
                    raise ValueError("archived conversations cannot resume execution")
                snapshot = await graph.aget_state({"configurable": {"thread_id": task_id}})
                if not snapshot.next and not snapshot.interrupts:
                    raise ValueError("checkpoint has no unfinished execution; send a new message")
                direct = self._direct_tool_call(str(task["input_text"]), task_id)
                if direct is not None and direct["name"] not in {"file_read", "file_write"}:
                    raise ValueError("direct command recovery supports only file_read/file_write")
                # Initial production recovery is deliberately file-only. Inspect
                # native retained history, not a truncated UI projection. This
                # may reject a turn that inherited earlier non-file tool calls.
                if any(
                    call["name"] not in {"file_read", "file_write"}
                    for message in snapshot.values.get("messages", []) if isinstance(message, AIMessage)
                    for call in message.tool_calls
                ):
                    raise ValueError("checkpoint includes tools outside file_read/file_write; replay is not supported")
            admitted = False
            try:
                if version is None:
                    await self.repository.update_task_status(task_id, "running")
                else:
                    await self.repository.resume_interrupted_task(workspace_id, task_id, version)
                admitted = True
                return await self._launch(None, request, graph=graph, initial_events=[
                    ("task.resumed", {"trace_id": trace_id, "execution_resumed": True,
                                      "principal_id": principal_id, "previous_version": task["version"]}),
                ])
            except asyncio.CancelledError:
                if not admitted:
                    raise
                await self.repository.cancel_task(workspace_id, task_id)
                await self._publish_event(request, "task.cancelled", {"message": "cancelled before recovery started"})
                raise
            except Exception:
                if not admitted:
                    raise
                # Admission failed before a root took ownership. Preserve the
                # checkpoint for an explicit retry, not a phantom running task.
                await self.repository.update_task_status(task_id, "interrupted", "recovery could not start")
                await self._publish_event(request, "task.interrupted", {"message": "recovery could not start"})
                raise

    async def answer_question(self, workspace_id: str, question_id: str, principal_id: str,
                              answer: str, version: int) -> RunHandle:
        question = await self.repository.get_question(workspace_id, question_id)
        async with self._conversation_locks[str(question["conversation_id"])]:
            active = self._active_runs.get(str(question["task_id"]))
            if active is not None:
                await asyncio.shield(active.wait())
            conversation = await self.repository.get_conversation(workspace_id, str(question["conversation_id"]))
            request = RuntimeRunRequest(
                workspace_id=workspace_id, conversation_id=str(question["conversation_id"]),
                task_id=str(question["task_id"]), principal_id=principal_id,
                permission_mode=str(conversation["permission_mode"]),
            )
            graph = await self._graph_for(request)
            snapshot = await graph.aget_state({"configurable": {"thread_id": request.task_id}})
            if not any(isinstance(item.value, dict) and item.value.get("kind") == "user_question"
                       and item.value.get("tool_call_id") == question["tool_call_id"]
                       for item in snapshot.interrupts):
                raise ValueError("question no longer matches the runtime checkpoint")
            question = await self.repository.answer_question(workspace_id, question_id, principal_id, answer, version)
            return await self._launch(None, request, graph=graph, initial_events=[
                ("question.answered", {"question_id": question_id, "answer": question["answer"],
                                       "version": question["version"]}),
            ])

    async def submit_input(self, workspace_id: str, task_id: str, content: str,
                           idempotency_key: str) -> dict[str, Any]:
        task = await self.repository.get_task(workspace_id, task_id)
        if str(task["input_text"]).startswith("/tool "):
            raise ValueError("direct tool commands cannot consume steering; send a new turn")
        existing = await self.repository.task_inputs(workspace_id, task_id)
        previous = next((item for item in existing if item["idempotency_key"] == idempotency_key), None)
        if previous is not None:
            if previous["content"] != content.strip():
                raise ValueError("idempotency key was already used for another message")
            return previous
        handle = self._active_runs.get(task_id)
        if handle is None or handle.root_task.done():
            raise ValueError("task is not executing; send a new turn")
        item = await self.repository.submit_task_input(workspace_id, task_id, content, idempotency_key)
        # Queued is only a receipt. Consumption is confirmed after a successful
        # model response containing this input, not merely after enqueueing it.
        await self._publish_event(RuntimeRunRequest(workspace_id=workspace_id,
            conversation_id=str(task["conversation_id"]), task_id=task_id),
            "task.input.queued", {"input_id": item["id"], "content": item["content"], "status": item["status"]})
        return item

    async def _question_interrupts(self, interrupts: Any, context: _RunContext) -> Command[Any] | None:
        """Project native interrupts and map durable user answers back to their IDs."""
        records = {item["tool_call_id"]: item for item in await self.repository.task_questions(
            context.request.workspace_id, context.request.task_id,
        )}
        answers: dict[str, str] = {}
        for item in interrupts:
            value = item.value
            if not isinstance(value, dict) or value.get("kind") != "user_question":
                raise RuntimeError("unsupported question interrupt")
            call_id = str(value["tool_call_id"])
            question = records.get(call_id)
            if question is not None and (question["title"] != value["title"]
                                         or json.loads(question["options_json"]) != value["options"]):
                raise PermissionError("question changed since it was displayed")
            if question is not None and question["status"] == "answered":
                answers[str(item.id)] = str(question["answer"])
                continue
            if question is None:
                question = await self.repository.request_question(
                    context.request.workspace_id, context.request.conversation_id, context.request.task_id,
                    call_id, context.request.principal_id, str(value["title"]), value["options"],
                )
            await self.repository.update_task_status(context.request.task_id, "waiting_approval")
            await self._emit(context, "question.requested", {
                "question_id": question["id"], "tool_call_id": call_id, "title": question["title"],
                "options": json.loads(question["options_json"]), "version": question["version"],
            })
        if len(answers) == len(interrupts):
            return Command(resume=answers)
        return None

    async def list_pending_approvals(
        self, workspace_id: str, conversation_id: str | None = None
    ) -> list[dict[str, Any]]:
        return await self.repository.list_approvals(workspace_id, conversation_id)

    async def _launch(
        self,
        graph_input: Any,
        request: RuntimeRunRequest,
        *,
        initial_events: Sequence[tuple[str, dict[str, Any]]] = (),
        graph: Any = None,
    ) -> RunHandle:
        self._require_open()
        existing = self._active_runs.get(request.task_id)
        if existing is not None:
            if existing.root_task.done():
                self._active_runs.pop(request.task_id, None)
            else:
                raise RuntimeError(f"task is already running: {request.task_id}")
        product_task = await self.repository.get_task(request.workspace_id, request.task_id)
        cancelled = product_task["status"] == "cancelled"
        if graph is None and not cancelled:
            graph = await self._graph_for(request)
        self._checkpoint_threads.add(request.task_id)
        queue: asyncio.Queue[MaigoKiteEvent | object] = asyncio.Queue()
        context = _RunContext(self, request, queue)
        context.direct_tool = None if cancelled else self._direct_tool_call(str(product_task["input_text"]), request.task_id)
        self._require_open()
        for event_type, payload in initial_events:
            await self._emit(context, event_type, payload)
        task = asyncio.create_task(
            self._drive(graph, graph_input, context),
            name=f"maigokite-langgraph:{request.task_id}",
        )
        handle = RunHandle(request, task, queue, context.started)
        self._active_runs[request.task_id] = handle

        def release(_completed: asyncio.Task[None]) -> None:
            context.started.set()
            if self._active_runs.get(request.task_id) is handle:
                self._active_runs.pop(request.task_id, None)

        task.add_done_callback(release)
        return handle

    @staticmethod
    def _direct_tool_call(prompt: str, task_id: str) -> NativeToolCall | None:
        if not prompt.startswith("/tool "):
            return None
        try:
            _, name, payload = prompt.split(" ", 2)
            arguments = json.loads(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("tool command format: /tool <name> <json-object>") from exc
        if not name or not isinstance(arguments, dict):
            raise ValueError("tool arguments must be a JSON object")
        return {"id": f"{task_id}_direct", "name": "exec_command" if name == "bash" else name, "args": arguments, "type": "tool_call"}

    async def _drive(self, graph: Any, graph_input: Any, context: _RunContext) -> None:
        config = {"configurable": {"thread_id": context.request.task_id}}
        try:
            context.started.set()
            await asyncio.sleep(0)
            task = await self.repository.get_task(context.request.workspace_id, context.request.task_id)
            context.max_subagent_calls = int(task.get("max_subagent_calls", 0))
            context.subagent_model_ids = json.loads(task.get("subagent_model_ids_json", "[]"))
            context.child_slots = asyncio.Semaphore(int(task.get("max_concurrent_subagents", 1)))
            if task["status"] == "cancelled":
                # A rejected/cancelled turn must never re-enter its checkpoint,
                # invoke tools, or ask a provider to acknowledge the rejection.
                await self._emit(context, "task.cancelled", {"message": "Task cancelled"})
                return
            # Preparation belongs to the root's cancellation/error boundary too,
            # including approval/question resumes whose decision already committed.
            request = context.request
            context.execution_metadata = (
                await self._execution_metadata(request) if self._execution_metadata else {
                    "workspace_id": request.workspace_id,
                    "workspace_root": str(self.workspace_root),
                    "conversation_id": request.conversation_id,
                    "principal_id": request.principal_id,
                    "permission_mode": request.permission_mode,
                }
            )
            await self._refresh_execution_metadata(context)
            if context.max_subagent_calls == 0 or "delegate" not in context.execution_metadata.get("enabled_tools", self._specs_by_name):
                context.execution_metadata["enabled_tools"] = [
                    name for name in context.execution_metadata.get("enabled_tools", self._specs_by_name)
                    if name not in {"delegate", "list_subagent_models"}
                ]
            if graph_input is None:
                snapshot = await graph.aget_state(config)
                if snapshot.interrupts:
                    message = next(
                        (
                            item for item in reversed(snapshot.values.get("messages", []))
                            if isinstance(item, AIMessage)
                        ),
                        None,
                    )
                    if message is None:
                        raise RuntimeError("approval checkpoint has no assistant tool calls")
                    await self._record_tool_proposals(message, context)
                    questions = all(isinstance(item.value, dict) and item.value.get("kind") == "user_question"
                                    for item in snapshot.interrupts)
                    if questions:
                        graph_input = await self._question_interrupts(snapshot.interrupts, context)
                        if graph_input is None:
                            context.interrupted = True
                            return
                    else:
                        graph_input = await self._review_resume_input(snapshot.interrupts, context)
                    if graph_input is None:
                        # Reviewing another item is a product projection only;
                        # do not restart the graph while its interrupt is pending.
                        await self._handle_interrupts(snapshot.interrupts, context)
                        return
            # Scope exits (including cancellation cleanup) before any parent
            # terminal status is published. No detached child task survives it.
            async with asyncio.TaskGroup() as children:
                context.child_scope = children
                async for event in graph.astream(
                    graph_input,
                    config=config,
                    context=context,
                    stream_mode=["messages", "updates"],
                    durability="sync",
                    version="v2",
                ):
                    await self._map_runtime_event(event, context)
            if context.interrupted:
                return
            await self._complete_reasoning(context)
            task = await self.repository.get_task(
                context.request.workspace_id, context.request.task_id
            )
            if str(task["status"]) == "cancelled":
                await self._emit(
                    context,
                    "task.cancelled",
                    {"message": "approval denied"},
                )
            else:
                await self.repository.update_task_status(
                    context.request.task_id, "succeeded"
                )
                await self._emit(context, "task.succeeded", {})
        except asyncio.CancelledError:
            task = await self.repository.cancel_task(
                context.request.workspace_id, context.request.task_id
            )
            # Completion may have committed immediately before stop arrived.
            # Do not publish cancelled over an immutable succeeded/failed row.
            status = str(task["status"])
            await self._emit(
                context,
                "task.cancelled" if status == "cancelled" else (
                    "task.succeeded" if status == "succeeded" else "task.failed"
                ),
                {"message": "cancelled by user" if status == "cancelled" else task.get("last_error", "")},
            )
            raise
        except Exception as exc:
            # Native TaskGroup groups a body error after draining children.
            # Keep a lone original error useful to users/inspection.
            while isinstance(exc, ExceptionGroup) and len(exc.exceptions) == 1:
                exc = exc.exceptions[0]
            task = await self.repository.get_task(
                context.request.workspace_id, context.request.task_id
            )
            if task["status"] == "cancelled":
                # A provider error while acknowledging a rejected tool batch
                # must not overwrite the user's cancellation with task.failed.
                await self._emit(context, "task.cancelled", {"message": "approval denied"})
            else:
                await self.repository.update_task_status(
                    context.request.task_id, "failed", str(exc)
                )
                await self._emit(
                    context,
                    "task.failed",
                    {
                        "message": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
        finally:
            await context.queue.put(_END)

    async def has_checkpoint(self, task_id: str) -> bool:
        checkpointer = self._require_open()
        checkpoint = await checkpointer.aget_tuple(
            {"configurable": {"thread_id": task_id}}
        )
        return checkpoint is not None

    async def cancel(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        """Cancel and await an active root task before publishing completion."""
        # Validate ownership before touching an in-memory handle.
        task = await self.repository.get_task(workspace_id, task_id)
        handle = self._active_runs.get(task_id)
        if handle is not None and not handle.root_task.done():
            await handle.cancel()
            return await self.repository.get_task(workspace_id, task_id)
        # Admission/resume owns this lock until its root is registered. Stop
        # must not race that gap and publish a terminal event before task.started.
        # Active execution above remains immediately cancellable without the lock.
        async with self._conversation_locks[str(task["conversation_id"])]:
            handle = self._active_runs.get(task_id)
            if handle is not None and not handle.root_task.done():
                await handle.cancel()
                return await self.repository.get_task(workspace_id, task_id)
            task = await self.repository.get_task(workspace_id, task_id)
            if str(task["status"]) in {"succeeded", "failed", "cancelled", "rejected", "timed_out", "expired"}:
                return task
            cancelled = await self.repository.cancel_task(workspace_id, task_id)
            if cancelled["status"] != "cancelled":
                return cancelled
            request = RuntimeRunRequest(
                workspace_id=workspace_id,
                conversation_id=str(cancelled["conversation_id"]),
                task_id=task_id,
            )
            await self._publish_event(
                request,
                "task.cancelled",
                {"message": "Cancelled by user"},
            )
            return cancelled

    async def _map_runtime_event(self, event: dict[str, Any], context: _RunContext) -> None:
        event_type = str(event.get("type") or "")
        data = event.get("data")
        if event_type == "messages" and isinstance(data, tuple) and data:
            metadata = data[1] if len(data) > 1 and isinstance(data[1], dict) else {}
            # Native summarization makes a model call too; its tokens are not
            # the user's answer. Only the public model node streams to the UI.
            if metadata.get("langgraph_node") != "model" or CHILD_TAG in metadata.get("tags", []):
                return
            await self._map_message(data[0], context)
            return
        if event_type != "updates" or not isinstance(data, dict):
            return
        interrupts = data.get("__interrupt__")
        if interrupts:
            await self._handle_interrupts(interrupts, context)
        for node, update in data.items():
            if not isinstance(update, dict):
                continue
            if isinstance(update.get("todos"), list):
                await self._emit(context, "plan.updated", {"items": update["todos"]})
            messages = update.get("messages")
            if not isinstance(messages, list):
                continue
            for message in messages:
                # HITL emits ToolMessages for rejected calls without invoking
                # the tool middleware. Project those results too.
                if isinstance(message, ToolMessage) and node in {
                    "tools", "HumanInTheLoopMiddleware.after_model"
                }:
                    await self._map_message(message, context)
                    continue
                if node != "model":
                    continue
                if not isinstance(message, AIMessage):
                    continue
                # Non-streaming integrations expose reasoning only on the final
                # message. Streaming updates contain the same text: don't repeat it.
                if not context.reasoning_streamed and (reasoning := self._reasoning_text(message)):
                    await self._append_reasoning(reasoning, context)
                context.reasoning_streamed = False
                await self._complete_reasoning(context)
                if message.tool_calls:
                    await self._record_tool_proposals(message, context)
                else:
                    content = self._message_text(message)
                    if content and not context.final_saved:
                        saved = await self.repository.append_message(
                            context.request.conversation_id,
                            "assistant",
                            content,
                        )
                        await self._emit(
                            context,
                            "message.completed",
                            {"content": content, "message_id": saved["id"]},
                        )
                        context.final_saved = True

    async def _map_message(self, message: BaseMessage, context: _RunContext) -> None:
        if isinstance(message, AIMessageChunk):
            reasoning = self._reasoning_text(message)
            if reasoning:
                context.reasoning_streamed = True
                await self._append_reasoning(reasoning, context)
            content = self._message_text(message)
            if content:
                await self._emit(
                    context,
                    "message.delta",
                    {"content": content},
                )
            return
        if isinstance(message, ToolMessage):
            call_id = str(message.tool_call_id or "")
            if not call_id or call_id in context.finished_tool_calls:
                return
            failed = getattr(message, "status", "success") == "error"
            content = self._message_text(message)
            product = message.artifact if isinstance(message.artifact, dict) else {}
            tool_name = str(message.name or context.tool_calls.get(call_id, {}).get("name", ""))
            summary = str(product.get("summary") or content)[:500]
            task = await self.repository.get_task(
                context.request.workspace_id, context.request.task_id
            )
            status = "failed" if failed else "succeeded"
            if failed and task["status"] == "cancelled":
                status = "denied"
            await self.repository.update_tool_call(
                call_id,
                status,
                result=product.get("data", {"content": content}),
                summary=summary,
            )
            await self.repository.record_audit(
                context.request.workspace_id,
                context.request.principal_id,
                "tool.failed" if failed else "tool.completed",
                tool_name,
                "failed" if failed else "success",
                {"tool_call_id": call_id, "summary": summary},
            )
            await self._emit(
                context,
                "tool.failed" if failed else "tool.completed",
                {
                    "tool_call_id": call_id,
                    "tool_name": tool_name,
                    "message": content,
                    "summary": summary,
                    "data": product.get("data", {"content": content}),
                    "error_code": product.get("error_code"),
                    "user_hint": product.get("user_hint"),
                    "action": product.get("action"),
                },
            )
            context.finished_tool_calls.add(call_id)

    async def _record_tool_proposals(
        self, message: AIMessage, context: _RunContext
    ) -> None:
        context.latest_tool_calls = []
        for raw_call in message.tool_calls:
            call: dict[str, Any] = {
                "id": str(raw_call.get("id") or f"call_{uuid.uuid4().hex}"),
                "name": str(raw_call.get("name") or ""),
                "args": dict(raw_call.get("args") or {}),
            }
            if call["name"] == "delegate" and any(item["id"] == call["id"] for item in context.latest_tool_calls):
                raise ValueError("delegate call IDs must be unique within a model turn")
            context.latest_tool_calls.append(call)
            context.tool_calls[call["id"]] = call
            try:
                stored = await self.repository.get_tool_call(call["id"])
            except KeyError:
                await self.repository.create_tool_call(
                    call["id"],
                    context.request.workspace_id,
                    context.request.conversation_id,
                    context.request.task_id,
                    call["name"],
                    call["args"],
                    self._message_text(message),
                )
                await self._emit(
                    context,
                    "tool.proposed",
                    {
                        "tool_call_id": call["id"],
                        "tool_name": call["name"],
                        "arguments": call["args"],
                    },
                )
            else:
                if (stored["workspace_id"] != context.request.workspace_id
                        or stored["conversation_id"] != context.request.conversation_id
                        or stored["task_id"] != context.request.task_id
                        or stored["tool_name"] != call["name"]):
                    raise ValueError("tool call ID already belongs to a different product operation")
                if call["name"] == "delegate" and (
                    stored["arguments_json"] != json.dumps(call["args"], ensure_ascii=False, sort_keys=True)
                    or call["id"] in context.finished_tool_calls
                ):
                    raise ValueError("delegate call IDs cannot be reused for another dispatch")

    def _matches_approval(self, record: dict[str, Any], name: str, decision: PolicyDecision) -> bool:
        return (
            record["tool_name"] == name
            and record["risk_level"] == decision.risk.name
            and self.repository.approval_matches_arguments(record, decision.arguments)
        )

    @staticmethod
    def _review_calls(interrupts: Any, ordered_calls: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Match native HITL actions to the checkpoint's ordered call IDs."""
        remaining = list(ordered_calls)
        calls: list[dict[str, Any]] = []
        for interrupt_value in interrupts:
            value = getattr(interrupt_value, "value", None)
            actions = value.get("action_requests") if isinstance(value, dict) else None
            if not isinstance(actions, list) or not actions:
                raise RuntimeError("unsupported runtime approval interrupt")
            for action in actions:
                index = next(
                    (
                        i for i, call in enumerate(remaining)
                        if call["name"] == action.get("name") and call["args"] == action.get("args")
                    ),
                    None,
                )
                if index is None:
                    raise RuntimeError("could not map HITL action to a checkpoint tool call")
                calls.append(remaining.pop(index))
        return calls

    async def _review_records(self, context: _RunContext) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for status in ("pending", "consumed", "rejected", "expired"):
            for record in await self.repository.list_approvals(
                context.request.workspace_id, context.request.conversation_id, status
            ):
                if record["task_id"] == context.request.task_id:
                    records[str(record["tool_call_id"])] = record
        return records

    async def _review_resume_input(
        self, interrupts: Any, context: _RunContext
    ) -> Command[Any] | None:
        """Translate existing approval audit facts into one native HITL response.

        Incomplete review leaves LangGraph interrupted. No continuation or
        separate batch state is stored; a new process derives this from the
        same checkpoint and Repository decisions.
        """
        calls = self._review_calls(interrupts, context.latest_tool_calls)
        context.review_call_ids = {call["id"] for call in calls}
        boundary_interrupts = [item for item in interrupts if item.value.get("source") == "tool_boundary"]
        context.boundary_review_ids = {
            call["id"] for call in self._review_calls(boundary_interrupts, context.latest_tool_calls)
        }
        records = await self._review_records(context)
        reviewed = [records.get(call["id"]) for call in calls]
        if any(record and record["status"] == "expired" for record in reviewed):
            raise PermissionError("approval has expired; start a new task")
        # Rejection is a terminal product cancellation, never a model turn.
        # This guard also refuses inconsistent historical product state.
        if any(record and record["status"] == "rejected" for record in reviewed):
            raise PermissionError("approval was rejected; this task cannot resume")
        for call, record in zip(calls, reviewed, strict=True):
            decision = self._policy_decision(call["name"], call["args"], context)
            if record is None and decision.authorization_id:
                # Native HITL still resumes the complete original batch. A
                # receipt can cover later siblings without inventing approvals.
                continue
            if record is None or record["status"] != "consumed":
                return None
            if decision.outcome == "deny" or not self._matches_approval(record, call["name"], decision):
                raise PermissionError("approved arguments no longer match the checkpoint tool call")
        return Command(resume={"decisions": [{"type": "approve"} for _ in calls]})

    async def _handle_interrupts(
        self, interrupts: Any, context: _RunContext
    ) -> None:
        task = await self.repository.get_task(context.request.workspace_id, context.request.task_id)
        if task["status"] == "cancelled":
            # A model must not reopen approval after the user rejected a batch.
            await self._emit(context, "task.cancelled", {"message": "approval denied"})
            context.interrupted = True
            return
        if all(isinstance(item.value, dict) and item.value.get("kind") == "user_question" for item in interrupts):
            await self._question_interrupts(interrupts, context)
            context.interrupted = True
            return
        records = await self._review_records(context)
        for call in self._review_calls(interrupts, context.latest_tool_calls):
            approval = records.get(call["id"])
            if approval is not None and approval["status"] == "consumed":
                # Also correct this projection after a crash between committing
                # the approval decision and exposing the next review item.
                await self.repository.update_tool_call(call["id"], "waiting_approval")
                continue
            if approval is not None and approval["status"] != "pending":
                raise PermissionError("approval is no longer pending")
            name = call["name"]
            decision = self._policy_decision(name, call["args"], context)
            if approval is None and decision.authorization_id:
                continue
            if decision.outcome == "deny" or (approval is None and decision.outcome != "approval_required"):
                raise RuntimeError("runtime interrupted for a tool the product policy did not gate")
            if approval is None:
                approval = await self.repository.create_approval(
                    context.request.workspace_id,
                    context.request.conversation_id,
                    context.request.principal_id,
                    context.request.task_id,
                    call["id"],
                    decision.arguments,
                    decision.risk.name,
                    reuse_scope=decision.reuse_scope,
                )
                await self.repository.record_audit(
                    context.request.workspace_id,
                    context.request.principal_id,
                    "approval.created",
                    str(approval["id"]),
                    "pending",
                    {
                        "tool_call_id": call["id"],
                        "tool_name": name,
                        "risk": decision.risk.name,
                    },
                )
            else:
                await self.repository.update_task_status(context.request.task_id, "waiting_approval")
            await self._emit(
                context,
                "task.waiting_approval",
                {
                    "tool_call_id": call["id"],
                    "approval_id": approval["id"],
                },
            )
            await self._emit(
                context,
                "approval.requested",
                self._approval_payload(approval),
            )
            context.interrupted = True
            # Keep the existing single-approval API and UI. The complete batch
            # stays in the native interrupt until the final decision arrives.
            return
        raise RuntimeError("runtime requested approval for an already reviewed batch")

    async def _execute_product_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        context = request.runtime.context
        if not isinstance(context, _RunContext):
            raise RuntimeError("LangGraph runtime context is missing")
        tool_name = str(request.tool_call["name"])
        await self._refresh_execution_metadata(context)
        authority = replace(context, execution_metadata=dict(context.execution_metadata))
        # Public dataclasses retain a per-operation snapshot, not a new runtime
        # state. Other operations cannot mutate this tool's captured authority.
        request = replace(request, runtime=replace(request.runtime, context=authority))
        task = await self.repository.get_task(context.request.workspace_id, context.request.task_id)
        if task["status"] == "cancelled":
            return ToolMessage(
                content="Task cancelled; this tool was not executed.",
                tool_call_id=str(request.tool_call["id"]),
                name=tool_name,
                status="error",
            )
        arguments = dict(request.tool_call.get("args") or {})
        if await self.repository.task_inputs(context.request.workspace_id, context.request.task_id, pending=True):
            return ToolMessage(
                content="New user input arrived. This proposed tool was not executed; reconsider it after reading the user's message.",
                tool_call_id=str(request.tool_call["id"]), name=tool_name, status="error",
            )
        decision = self._policy_decision(tool_name, arguments, authority)
        approved = next((record for record in await self.repository.list_approvals(
            context.request.workspace_id, context.request.conversation_id, "consumed",
        ) if record["task_id"] == context.request.task_id
            and record["tool_call_id"] == request.tool_call["id"]), None)
        if (request.tool_call["id"] in context.boundary_review_ids
                or (decision.outcome == "approval_required" and approved is None)):
            # A permission change can occur after after_model HITL, while an
            # earlier tool is executing. Suspend this ToolNode through native
            # LangGraph interrupt; existing Approval API/audit still authorize it.
            interrupt({
                "action_requests": [{"name": tool_name, "args": arguments,
                                     "description": decision.reason}],
                "review_configs": [{"action_name": tool_name, "allowed_decisions": ["approve", "reject"]}],
                "source": "tool_boundary",
            })
        if approved is not None or decision.outcome == "approval_required":
            # HITL owns suspension/resume. The product audit still owns the
            # authorization, including replay directly into a ToolNode after
            # the approval interrupt has already been checkpointed away.
            decision = self._policy_decision(tool_name, arguments, authority, approved=approved is not None)
            if approved is None or not self._matches_approval(approved, tool_name, decision):
                return ToolMessage(
                    content="No matching approval for these tool parameters; this tool was not executed.",
                    tool_call_id=str(request.tool_call["id"]), name=tool_name, status="error",
                )
        if decision.outcome != "allow":
            # ToolNode still projects the returned failure to the model and UI;
            # a hidden/disabled call never reaches the actual tool body.
            return ToolMessage(
                content=decision.reason, tool_call_id=str(request.tool_call["id"]),
                name=tool_name, status="error",
            )
        if decision.authorization_id:
            await self.repository.record_audit(
                context.request.workspace_id, context.request.principal_id,
                "authorization.used", decision.authorization_id, "allowed",
                {"task_id": context.request.task_id, "tool_call_id": request.tool_call["id"], "tool_name": tool_name},
            )
        # Only a successful product policy decision selects the execution
        # boundary. Tool arguments can request escalation, never grant it.
        authority.execution_metadata["sandbox_mode"] = decision.sandbox_mode
        authority.execution_metadata["allow_network"] = decision.allow_network
        call_id = str(request.tool_call.get("id") or "")
        request = request.override(
            tool_call={**request.tool_call, "args": decision.arguments}
        )
        await self.repository.update_tool_call(
            call_id,
            "running",
            arguments=decision.arguments,
            risk_level=decision.risk.name,
        )
        await self._emit(
            context,
            "tool.started",
            {
                "tool_call_id": call_id,
                "tool_name": tool_name,
                "arguments": decision.arguments,
                "resource_scope": decision.resource_scope,
                "risk_level": decision.risk.name,
                "sandbox_mode": decision.sandbox_mode,
                "allow_network": decision.allow_network,
            },
        )
        try:
            result = await handler(request)
        except GraphInterrupt:
            # LangGraph owns the suspension; asking a question is not a failed tool.
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self.repository.update_tool_call(
                call_id, "failed", summary=str(exc)
            )
            await self._emit(
                context,
                "tool.failed",
                {
                    "tool_call_id": call_id,
                    "tool_name": tool_name,
                    "message": str(exc),
                },
            )
            context.finished_tool_calls.add(call_id)
            raise
        failed = isinstance(result, ToolMessage) and result.status == "error"
        content = self._message_text(result)
        product = result.artifact if isinstance(result, ToolMessage) and isinstance(result.artifact, dict) else {}
        summary = str(product.get("summary") or content)[:500]
        data = product.get("data", {"content": content})
        status = "failed" if failed else "succeeded"
        await self.repository.update_tool_call(
            call_id,
            status,
            result=data,
            summary=summary,
        )
        await self.repository.record_audit(
            context.request.workspace_id,
            context.request.principal_id,
            "tool.failed" if failed else "tool.completed",
            tool_name,
            "failed" if failed else "success",
            {"risk": decision.risk.name, "summary": summary},
        )
        await self._emit(
            context,
            "tool.failed" if failed else "tool.completed",
            {
                "tool_call_id": call_id,
                "tool_name": tool_name,
                "summary": summary,
                "data": data,
                "result": data,
                "error_code": product.get("error_code"),
                "user_hint": product.get("user_hint"),
                "action": product.get("action"),
            },
        )
        context.finished_tool_calls.add(call_id)
        change = product.get("file_change")
        if not failed and isinstance(change, dict):
            await self._emit(context, "file.changed", {**change, "tool_call_id": call_id})
        return result

    async def _emit(
        self,
        context: _RunContext,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        async with context.event_lock:
            if context.terminal_emitted:
                return
            enriched = await self._publish_event(context.request, event_type, payload)
            if event_type in {"task.cancelled", "task.failed", "task.succeeded", "task.interrupted"}:
                context.terminal_emitted = True
            await context.queue.put(MaigoKiteEvent(event_type, enriched))

    async def _publish_event(
        self,
        request: RuntimeRunRequest,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        base = {
            "task_id": request.task_id,
            "conversation_id": request.conversation_id,
            **payload,
        }
        if self._event_publisher is not None:
            await self._event_publisher(event_type, base)
            return base
        return await self.repository.append_task_event(event_type, base)

    @staticmethod
    def _approval_payload(approval: dict[str, Any]) -> dict[str, Any]:
        arguments = dict(approval.get("arguments") or {})
        return {
            "approval_id": approval["id"],
            "task_id": approval["task_id"],
            "conversation_id": approval["conversation_id"],
            "tool_call_id": approval["tool_call_id"],
            "tool_name": approval["tool_name"],
            "arguments": arguments,
            "resource_scope": str(
                arguments.get("path")
                or arguments.get("root_dir")
                or arguments.get("workdir")
                or arguments.get("url")
                or "current workspace"
            ),
            "risk_level": approval["risk_level"],
            "status": approval["status"],
            "version": int(approval["version"]),
            "expires_at": approval["expires_at"],
            "note": approval.get("note", ""),
            "decided_at": approval.get("decided_at") or "",
            "reuse_scope": approval.get("reuse_scope") or {},
            "allowed_scopes": ["once", "task", "session"] if approval.get("reuse_scope") else ["once"],
            "authorization_scope": approval.get("authorization_scope", "once"),
            "authorization_expires_at": approval.get("authorization_expires_at", ""),
            "authorization_revoked_at": approval.get("authorization_revoked_at", ""),
        }

    @staticmethod
    def _message_text(message: Any) -> str:
        value = getattr(message, "content", message)
        if isinstance(value, str):
            return value
        if not isinstance(value, list):
            return ""
        parts: list[str] = []
        for block in value:
            if isinstance(block, str):
                parts.append(block)
            elif (
                isinstance(block, dict)
                and block.get("type") not in {"reasoning", "thinking"}
                and isinstance(block.get("text"), str)
            ):
                parts.append(block["text"])
        return "".join(parts)

    async def _append_reasoning(self, text: str, context: _RunContext) -> None:
        if not context.reasoning_started or context.reasoning_completed:
            await self._emit(context, "reasoning.started", {})
            if context.reasoning_parts:
                text = "\n\n" + text
            context.reasoning_started = True
            context.reasoning_completed = False
        context.reasoning_parts.append(text)
        await self._emit(context, "reasoning.delta", {"content": text})

    async def _complete_reasoning(self, context: _RunContext) -> None:
        if context.reasoning_started and not context.reasoning_completed:
            await self._emit(context, "reasoning.completed", {"summary": "".join(context.reasoning_parts)})
            context.reasoning_completed = True

    @staticmethod
    def _reasoning_text(message: Any) -> str:
        # Prefer LangChain's public normalized blocks (including Responses API
        # summaries and Anthropic thinking); aliases are a compatible fallback.
        parts = [visible_reasoning(block) for block in getattr(message, "content_blocks", [])
                 if isinstance(block, dict) and block.get("type") in {"reasoning", "thinking"}]
        if text := "".join(parts):
            return text
        additional = getattr(message, "additional_kwargs", {}) or {}
        for key in ("reasoning_content", "reasoning", "thinking", "reasoning_details"):
            if text := visible_reasoning(additional.get(key)):
                return text
        return ""
