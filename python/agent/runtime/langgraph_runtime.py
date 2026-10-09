"""Production glue between Nanami product semantics and LangGraph.

LangChain owns the agent loop and tool orchestration.  This module owns only
runtime invocation, stable Nanami event projection, approval bridging, and
product persistence projection.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, HumanInTheLoopMiddleware, ModelCallLimitMiddleware
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain.agents.middleware.types import ModelRequest, ModelResponse, ToolCallRequest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.tools import StructuredTool
from langchain_anthropic import ChatAnthropic
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent.repository import SQLiteRepository
from agent.models.usage import message_usage
from agent.runtime.context import ContextBudgetMiddleware, SafeSummarizationMiddleware
from agent.tools.base import BaseTool
from agent.tools.native.file_read import FileReadTool
from agent.tools.native.file_write import FileWriteTool
from agent.tools.permission_mgr import PermissionManager, PolicyDecision, RiskLevel
from agent.tools.validator import ToolValidator, ValidationError


@dataclass(frozen=True, slots=True)
class NanamiEvent:
    """A stable product event that does not expose LangGraph event classes."""

    type: str
    payload: dict[str, Any]


EventPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]
ModelResolver = Callable[[str, str], Awaitable[tuple[str, BaseChatModel]]]


@dataclass(frozen=True, slots=True)
class RuntimeRunRequest:
    workspace_id: str = "personal"
    conversation_id: str = ""
    task_id: str = ""
    principal_id: str = "local-user"
    permission_mode: str = "read_only"
    trace_id: str = ""


@dataclass(frozen=True, slots=True)
class ProductToolSpec:
    """The only bridge needed for a migrated Nanami tool."""

    tool: BaseTool
    runtime_tool: StructuredTool


_END = object()


class RunHandle:
    """One run owns one root asyncio task and an event queue."""

    def __init__(
        self,
        request: RuntimeRunRequest,
        root_task: asyncio.Task[None],
        queue: asyncio.Queue[NanamiEvent | object],
    ) -> None:
        self.request = request
        self.root_task = root_task
        self._queue = queue

    async def events(self) -> AsyncIterator[NanamiEvent]:
        while True:
            item = await self._queue.get()
            if item is _END:
                return
            assert isinstance(item, NanamiEvent)
            yield item

    async def collect(self) -> list[NanamiEvent]:
        return [event async for event in self.events()]

    async def wait(self) -> None:
        await self.root_task

    async def cancel(self) -> None:
        if not self.root_task.done():
            self.root_task.cancel()
        try:
            await self.root_task
        except asyncio.CancelledError:
            pass


@dataclass(slots=True)
class _RunContext:
    adapter: "LangGraphRuntime"
    request: RuntimeRunRequest
    queue: asyncio.Queue[NanamiEvent | object]
    execution_metadata: dict[str, Any] = field(default_factory=dict)
    tool_calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    latest_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finished_tool_calls: set[str] = field(default_factory=set)
    reasoning_parts: list[str] = field(default_factory=list)
    reasoning_started: bool = False
    reasoning_completed: bool = False
    final_saved: bool = False
    interrupted: bool = False
    tool_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class _ProductToolMiddleware(AgentMiddleware):
    """Map official tool execution callbacks to Nanami product concerns."""

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        enabled = request.runtime.context.execution_metadata.get("enabled_tools")
        if enabled is not None:
            request = request.override(tools=[tool for tool in request.tools if getattr(tool, "name", "") in enabled])
        return await handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        context = request.runtime.context
        if not isinstance(context, _RunContext):
            raise RuntimeError("LangGraph runtime context is missing")
        # ToolNode retains orchestration and results. Serialize tool bodies
        # during migration, including writes to the same file in one batch.
        async with context.tool_lock:
            return await context.adapter._execute_product_tool_call(request, handler)


class LangGraphRuntime:
    """Thin production adapter using framework loop, persistence, and HITL."""

    def __init__(
        self,
        *,
        model: BaseChatModel | None = None,
        model_resolver: ModelResolver | None = None,
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
        self._active_runs: dict[str, RunHandle] = {}
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

    def _create_graph(self, model: BaseChatModel) -> Any:
        runtime_tools = [spec.runtime_tool for spec in self.tool_specs]
        interrupt_on: dict[str, bool | InterruptOnConfig] = {
            spec.tool.name: InterruptOnConfig(
                allowed_decisions=["approve", "reject"],
                when=self._should_interrupt,
                description=cast(Any, self._approval_description),
            )
            for spec in self.tool_specs
        }
        overhead = count_tokens_approximately(
            [SystemMessage(self.system_prompt)] if self.system_prompt else [],
            tools=[*runtime_tools],
        )
        history_budget = max(1, self.context_max_tokens - overhead)
        middleware: list[AgentMiddleware[Any, Any, Any]] = [
            _ProductToolMiddleware(),
            ModelCallLimitMiddleware(thread_limit=self.max_model_calls, exit_behavior="error"),
            SafeSummarizationMiddleware(
                model=model,
                trigger=("tokens", max(1, int(history_budget * 0.8))),
                keep=("tokens", max(1, int(history_budget * 0.4))),
                # Do not silently drop the beginning before summarizing it.
                # An already oversized import may fail at the provider; the
                # safety wrapper keeps its checkpoint rather than losing data.
                trim_tokens_to_summarize=None,
            ),
            ContextBudgetMiddleware(self.context_max_tokens),
            HumanInTheLoopMiddleware(interrupt_on),
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
            name="nanami-langgraph-runtime",
        )

    async def close(self) -> None:
        handles = list(self._active_runs.values())
        if handles:
            await asyncio.gather(
                *(handle.cancel() for handle in handles), return_exceptions=True
            )
        self._active_runs.clear()
        self._graphs.clear()
        await asyncio.sleep(0)
        if self._checkpointer is not None:
            for task_id in self._checkpoint_threads:
                await self._checkpointer.aget_tuple(
                    {"configurable": {"thread_id": task_id}}
                )
        self._checkpoint_threads.clear()
        self._checkpointer = None
        if self._checkpointer_context is not None:
            await self._checkpointer_context.__aexit__(None, None, None)
            self._checkpointer_context = None
        if self._owns_repository:
            await self.repository.close()
        self._opened = False

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
            request.workspace_id, str(conversation.get("model_id") or "")
        )
        graph = self._graphs.get(key)
        if graph is None:
            graph = self._create_graph(model)
            self._graphs[key] = graph
        return graph

    def _policy_decision(
        self, name: str, arguments: dict[str, Any], context: _RunContext, *, approved: bool = False,
    ) -> PolicyDecision:
        spec = self._specs_by_name.get(name)
        enabled = context.execution_metadata.get("enabled_tools", self._specs_by_name)
        if spec is None or name not in enabled:
            return PolicyDecision("deny", RiskLevel.L5, "tool is not enabled for this run", arguments)
        try:
            clean = self._validator.sanitize(name, arguments)
        except ValidationError as exc:
            return PolicyDecision("deny", RiskLevel.L5, str(exc), arguments)
        return self.policy.evaluate(
            name,
            clean,
            approved=approved,
            risk_override=getattr(spec.tool, "risk_level", None),
            mode=context.request.permission_mode,
        )

    def _should_interrupt(self, tool_request: Any) -> bool:
        context = tool_request.runtime.context
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
        history = await self.repository.list_messages(actual.conversation_id)
        await self.repository.create_task_state(
            task_id,
            actual.workspace_id,
            actual.conversation_id,
            prompt[:80] or "Agent task",
            "running",
            prompt,
        )
        await self.repository.append_message(actual.conversation_id, "user", prompt)
        messages = [
            {"role": str(item["role"]), "content": str(item["content"])}
            for item in history
            if str(item.get("role")) in {"user", "assistant", "system"}
        ]
        messages.append({"role": "user", "content": prompt})
        return await self._launch(
            {"messages": messages},
            actual,
            initial_events=[
                ("task.started", {"trace_id": actual.trace_id})
            ],
        )

    async def resume_approval(
        self,
        workspace_id: str,
        approval_id: str,
        principal_id: str,
        decision: str,
        version: int,
    ) -> RunHandle:
        self._require_open()
        approval = await self.repository.decide_approval(
            workspace_id, approval_id, principal_id, decision, version
        )
        if decision == "allow":
            # The legacy API marks an approved tool running immediately. Here
            # it still waits for the rest of the native HITL batch to be reviewed.
            await self.repository.update_tool_call(
                str(approval["tool_call_id"]), "waiting_approval"
            )
        await self.repository.record_audit(
            workspace_id,
            principal_id,
            "approval.decided",
            approval_id,
            "approved" if decision == "allow" else "denied",
            {
                "tool_call_id": approval["tool_call_id"],
                "tool_name": approval["tool_name"],
            },
        )
        task = await self.repository.get_task(workspace_id, str(approval["task_id"]))
        conversation = await self.repository.get_conversation(
            workspace_id, str(task["conversation_id"])
        )
        request = RuntimeRunRequest(
            workspace_id=workspace_id,
            conversation_id=str(task["conversation_id"]),
            task_id=str(task["id"]),
            principal_id=principal_id,
            permission_mode=str(conversation["permission_mode"]),
        )
        return await self._launch(
            # Repository stores the user's decision, not execution state.
            # _drive resumes the native HITL batch only when review is complete.
            None,
            request,
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

    async def recover(self, workspace_id: str, task_id: str) -> RunHandle:
        """Continue the latest checkpoint without inventing a continuation payload."""
        self._require_open()
        task = await self.repository.get_task(workspace_id, task_id)
        conversation = await self.repository.get_conversation(
            workspace_id, str(task["conversation_id"])
        )
        if str(task["status"]) not in {"cancelled", "succeeded", "failed"}:
            await self.repository.update_task_status(task_id, "running")
        request = RuntimeRunRequest(
            workspace_id=workspace_id,
            conversation_id=str(task["conversation_id"]),
            task_id=task_id,
            permission_mode=str(conversation["permission_mode"]),
        )
        return await self._launch(None, request)

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
    ) -> RunHandle:
        existing = self._active_runs.get(request.task_id)
        if existing is not None:
            if existing.root_task.done():
                self._active_runs.pop(request.task_id, None)
            else:
                raise RuntimeError(f"task is already running: {request.task_id}")
        graph = await self._graph_for(request)
        self._checkpoint_threads.add(request.task_id)
        queue: asyncio.Queue[NanamiEvent | object] = asyncio.Queue()
        context = _RunContext(self, request, queue)
        context.execution_metadata = (
            await self._execution_metadata(request) if self._execution_metadata else {
                "workspace_id": request.workspace_id,
                "workspace_root": str(self.workspace_root),
                "conversation_id": request.conversation_id,
                "principal_id": request.principal_id,
                "permission_mode": request.permission_mode,
            }
        )
        for event_type, payload in initial_events:
            await self._emit(context, event_type, payload)
        task = asyncio.create_task(
            self._drive(graph, graph_input, context),
            name=f"nanami-langgraph:{request.task_id}",
        )
        handle = RunHandle(request, task, queue)
        self._active_runs[request.task_id] = handle

        def release(_completed: asyncio.Task[None]) -> None:
            if self._active_runs.get(request.task_id) is handle:
                self._active_runs.pop(request.task_id, None)

        task.add_done_callback(release)
        return handle

    async def _drive(self, graph: Any, graph_input: Any, context: _RunContext) -> None:
        config = {"configurable": {"thread_id": context.request.task_id}}
        try:
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
                    graph_input = await self._review_resume_input(snapshot.interrupts, context)
                    if graph_input is None:
                        # Reviewing another item is a product projection only;
                        # do not restart the graph while its interrupt is pending.
                        await self._handle_interrupts(snapshot.interrupts, context)
                        return
            async for event in graph.astream(
                graph_input,
                config=config,
                context=context,
                stream_mode=["messages", "updates"],
                version="v2",
            ):
                await self._map_runtime_event(event, context)
            if context.interrupted:
                return
            if context.reasoning_started and not context.reasoning_completed:
                await self._emit(
                    context,
                    "reasoning.completed",
                    {"summary": "".join(context.reasoning_parts)},
                )
                context.reasoning_completed = True
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
            await self.repository.cancel_task(
                context.request.workspace_id, context.request.task_id
            )
            await self._emit(
                context,
                "task.cancelled",
                {"message": "cancelled by user"},
            )
            raise
        except Exception as exc:
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

    async def owns_task(self, task_id: str) -> bool:
        return task_id in self._active_runs or await self.has_checkpoint(task_id)

    async def cancel(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        """Cancel and await an active root task before publishing completion."""
        handle = self._active_runs.get(task_id)
        if handle is not None:
            await handle.cancel()
            return await self.repository.get_task(workspace_id, task_id)
        task = await self.repository.get_task(workspace_id, task_id)
        if str(task["status"]) in {"succeeded", "failed", "cancelled", "timed_out", "expired"}:
            return task
        cancelled = await self.repository.cancel_task(workspace_id, task_id)
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
            if metadata.get("langgraph_node") != "model":
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
                if usage := message_usage(message):
                    await self._emit(context, "model.usage", {"usage": usage, "purpose": "response"})
                if message.tool_calls:
                    await self._record_tool_proposals(message, context)
                else:
                    content = self._message_text(message)
                    if content and not context.final_saved:
                        if context.reasoning_started and not context.reasoning_completed:
                            await self._emit(
                                context,
                                "reasoning.completed",
                                {"summary": "".join(context.reasoning_parts)},
                            )
                            context.reasoning_completed = True
                        await self.repository.append_message(
                            context.request.conversation_id,
                            "assistant",
                            content,
                        )
                        await self._emit(
                            context,
                            "message.completed",
                            {"content": content},
                        )
                        context.final_saved = True

    async def _map_message(self, message: BaseMessage, context: _RunContext) -> None:
        if isinstance(message, AIMessageChunk):
            reasoning = self._reasoning_text(message)
            if reasoning:
                if not context.reasoning_started:
                    await self._emit(context, "reasoning.started", {})
                    context.reasoning_started = True
                context.reasoning_parts.append(reasoning)
                await self._emit(
                    context,
                    "reasoning.delta",
                    {"content": reasoning},
                )
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
                str(message.name or ""),
                "failed" if failed else "success",
                {"tool_call_id": call_id, "summary": summary},
            )
            await self._emit(
                context,
                "tool.failed" if failed else "tool.completed",
                {
                    "tool_call_id": call_id,
                    "tool_name": str(message.name or ""),
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
            context.latest_tool_calls.append(call)
            context.tool_calls[call["id"]] = call
            try:
                await self.repository.get_tool_call(call["id"])
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

    @staticmethod
    def _review_calls(interrupts: Any, context: _RunContext) -> list[dict[str, Any]]:
        """Match native HITL actions to the checkpoint's ordered call IDs."""
        remaining = list(context.latest_tool_calls)
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
        calls = self._review_calls(interrupts, context)
        required = [
            call["id"] for call in context.latest_tool_calls
            if self._policy_decision(call["name"], call["args"], context).outcome == "approval_required"
        ]
        if required != [call["id"] for call in calls]:
            raise PermissionError("permission policy changed during approval; cancel and start a new task")
        records = await self._review_records(context)
        reviewed = [records.get(call["id"]) for call in calls]
        if any(record and record["status"] == "expired" for record in reviewed):
            raise PermissionError("approval has expired; start a new task")
        # Denying one action cancels the still-unexecuted protected batch.
        # Native HITL creates matching error ToolMessages for every action.
        if any(record and record["status"] == "rejected" for record in reviewed):
            return Command(resume={"decisions": [
                {"type": "reject", "message": "Approval denied; this tool batch was not executed."}
                for _ in calls
            ]})
        if any(record is None or record["status"] != "consumed" for record in reviewed):
            return None
        for call, record in zip(calls, reviewed, strict=True):
            assert record is not None
            decision = self._policy_decision(call["name"], call["args"], context)
            if record["arguments"] != decision.arguments:
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
        records = await self._review_records(context)
        for call in self._review_calls(interrupts, context):
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
            if decision.outcome != "approval_required":
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
        if self._execution_metadata is not None:
            fresh = await self._execution_metadata(context.request)
            # A run's tool declarations stay stable. Revocation narrows them
            # immediately; enabling a tool never grants an in-flight proposal.
            original = context.execution_metadata.get("enabled_tools", self._specs_by_name)
            fresh["enabled_tools"] = sorted(set(original) & set(fresh.get("enabled_tools", original)))
            context.execution_metadata = fresh
            if fresh.get("permission_mode", context.request.permission_mode) != context.request.permission_mode:
                raise PermissionError("permission mode changed; start a new task")
        task = await self.repository.get_task(context.request.workspace_id, context.request.task_id)
        if task["status"] == "cancelled":
            return ToolMessage(
                content="Task cancelled; this tool was not executed.",
                tool_call_id=str(request.tool_call["id"]),
                name=tool_name,
                status="error",
            )
        arguments = dict(request.tool_call.get("args") or {})
        decision = self._policy_decision(tool_name, arguments, context, approved=True)
        if decision.outcome != "allow":
            # ToolNode still projects the returned failure to the model and UI;
            # a hidden/disabled call never reaches the actual tool body.
            return ToolMessage(
                content=decision.reason, tool_call_id=str(request.tool_call["id"]),
                name=tool_name, status="error",
            )
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
            },
        )
        try:
            result = self._reconcile_file_write(
                tool_name, call_id, decision.arguments
            )
            if result is None:
                result = await handler(request)
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
        return result

    @staticmethod
    def _reconcile_file_write(
        tool_name: str, call_id: str, arguments: dict[str, Any]
    ) -> ToolMessage | None:
        """Treat an already-satisfied file content write as safely reconciled."""
        if tool_name != "file_write":
            return None
        path = arguments.get("path")
        content = arguments.get("content")
        encoding = arguments.get("encoding", "utf-8")
        if (
            not isinstance(path, str)
            or not isinstance(content, str)
            or not isinstance(encoding, str)
        ):
            return None
        target = Path(path)
        if not target.is_file():
            return None
        try:
            current = target.read_text(encoding=encoding)
        except (LookupError, OSError, UnicodeError):
            return None
        if current != content:
            return None
        payload = {
            "path": path,
            "bytes_written": len(content.encode(encoding)),
            "reconciled": True,
        }
        return ToolMessage(
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=call_id,
            name=tool_name,
            status="success",
        )

    async def _emit(
        self,
        context: _RunContext,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        enriched = await self._publish_event(context.request, event_type, payload)
        await context.queue.put(NanamiEvent(event_type, enriched))

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

    @staticmethod
    def _reasoning_text(message: Any) -> str:
        additional = getattr(message, "additional_kwargs", {}) or {}
        parts: list[str] = []
        for key in ("reasoning_content", "reasoning", "thinking"):
            value = additional.get(key)
            if isinstance(value, str):
                parts.append(value)
        content = getattr(message, "content", None)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") not in {"reasoning", "thinking"}:
                    continue
                value = block.get("text") or block.get("reasoning") or block.get("thinking")
                if isinstance(value, str):
                    parts.append(value)
        return "".join(parts)
