"""Small product safety guards around LangChain's context middleware."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, SummarizationMiddleware
from langchain.agents.middleware.summarization import DEFAULT_SUMMARY_PROMPT
from langchain.agents.middleware.types import AgentState, ExtendedModelResponse, ModelRequest, ModelResponse
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately, merge_message_runs
from langgraph.constants import TAG_NOSTREAM
from langgraph.types import Command

from agent.models.context_capacity import (
    ContextCapacity,
    capacity_from_error,
    is_context_overflow,
    profile_capacity,
    resolve_context_capacity,
)
from agent.models.usage import message_usage


class ContextBudgetExceeded(ValueError):
    """A request needs smaller inputs, not silent loss of its instructions."""

    def __init__(self, message: str, *, reason: str = "") -> None:
        super().__init__(message)
        self.reason = reason


def _output_field(model: Any) -> str | None:
    return next((name for name in ("max_tokens", "max_completion_tokens", "num_predict")
                 if name in getattr(type(model), "model_fields", {})), None)


def _minimum_output(model: Any) -> int:
    # Anthropic's explicit thinking budget must remain below its output cap.
    # Never disable thinking or change effort just to make a request fit.
    thinking = getattr(model, "thinking", None)
    budget = thinking.get("budget_tokens") if isinstance(thinking, dict) else None
    return budget + 1 if type(budget) is int and budget > 0 else 1


def _output_reserve(model: Any, capacity: ContextCapacity | None = None) -> int:
    requested = next((value for name in ("max_tokens", "max_completion_tokens", "num_predict")
                      if type(value := getattr(model, name, None)) is int and value > 0), 0)
    capacity = capacity if capacity is not None else profile_capacity(model)
    if not requested or capacity.tokens is None:
        return requested
    # A request policy, not a model-name table or a saved configuration change.
    # Keep at least three quarters of a known window available to input before
    # safety headroom. The SDK copy below sends this very same cap to the server.
    return min(requested, max(capacity.tokens // 4, _minimum_output(model)))


def _safety_margin(capacity: ContextCapacity) -> int:
    # Token counts remain estimates. This is budget headroom, NOT extra usage.
    if capacity.tokens:
        return min(1024, max(128, capacity.tokens // 20))
    return 0


def effective_input_budget(model: Any, configured: int, capacity: ContextCapacity | None = None) -> int:
    """Use the same observed window for compaction, admission and UI projection."""
    capacity = capacity if capacity is not None else profile_capacity(model)
    if capacity.tokens is None:
        return configured
    # The legacy product default must not cap every known deployment at 32k.
    # It sizes recovery work only when there is no capacity evidence.
    budget = max(1, capacity.tokens - _output_reserve(model, capacity) - _safety_margin(capacity))
    metadata = getattr(model, "metadata", None) or {}
    input_limit = metadata.get("maigokite_catalog_input_limit") if capacity.source == "models.dev" else None
    # Some catalogs distinguish the combined window from a smaller input cap.
    return min(budget, input_limit) if type(input_limit) is int and input_limit > 0 else budget


def context_payload(model: Any, capacity: ContextCapacity, configured: int) -> dict[str, Any]:
    """One capacity/budget projection for discovery and execution receipts."""
    metadata = getattr(model, "metadata", None) or {}
    budget = effective_input_budget(model, configured, capacity) if capacity.tokens else None
    return {
        "model_name": str(getattr(model, "model_name", None) or getattr(model, "model", "")),
        "model_id": metadata.get("maigokite_model_id", ""),
        "model_key": metadata.get("maigokite_model_key", ""),
        "model_context_window": capacity.tokens,
        "capacity_source": capacity.source, "capacity_status": capacity.status,
        "capacity_checked_at": capacity.checked_at,
        "input_budget_tokens": budget, "output_reserved_tokens": _output_reserve(model, capacity),
        "safety_margin_tokens": _safety_margin(capacity),
        "compaction_trigger_tokens": int(budget * 0.8) if budget else None,
    }


async def _emit(context: Any, kind: str, payload: dict[str, Any]) -> None:
    if getattr(context, "adapter", None) is not None:
        parent = getattr(context, "parent", None)
        if parent is not None:
            # Child usage is charged to the same turn, without replacing the
            # main conversation's context meter or streaming its answer.
            if kind.startswith("model."):
                await context.adapter._emit(parent, kind, {
                    **payload, **context.model_info, "purpose": "subagent", "subagent_id": context.subagent_id,
                })
        else:
            await context.adapter._emit(context, kind, payload)


async def _charge_call(context: Any) -> None:
    if getattr(context, "adapter", None) is not None:
        await context.adapter.repository.reserve_model_call(
            context.request.workspace_id, context.request.task_id,
            child=getattr(context, "parent", None) is not None,
        )


async def _publish_context(
    context: Any, model: Any, capacity: ContextCapacity, configured: int, used: int, *,
    call_id: str, measurement: str = "estimate", purpose: str = "response",
) -> None:
    await _emit(context, "context.updated", {
        **context_payload(model, capacity, configured),
        "call_id": call_id, "estimated_input_tokens": used,
        "measurement": measurement, "purpose": purpose,
        "context_percent": used / capacity.tokens * 100 if capacity.tokens else None,
    })


class _TokenClock(AsyncCallbackHandler):
    """Request-local timing via SDK callbacks; no token counting or transport ownership."""

    def __init__(self) -> None:
        self.first_token_at: float | None = None

    async def on_llm_new_token(
        self, token: str | list[str | dict[str, Any]], *, chunk: Any = None, **kwargs: Any,
    ) -> None:
        message = getattr(chunk, "message", None)
        meaningful = token or getattr(message, "content", None) or getattr(message, "tool_call_chunks", None)
        if not meaningful:
            extra = getattr(message, "additional_kwargs", {}) or {}
            meaningful = extra.get("reasoning_content") or extra.get("thinking")
        if meaningful and self.first_token_at is None:
            self.first_token_at = time.perf_counter()


class _SummaryObservation(AsyncCallbackHandler):
    """Observe one SDK summary call, not a second invocation/retry mechanism."""

    raise_error = True

    def __init__(self, context: Any, input_budget: int, model: Any = None, configured: int = 32000) -> None:
        self.context = context
        self.input_budget = input_budget
        self.model = model
        self.configured = configured
        self.truncated = False
        self.error: BaseException | None = None

    async def on_chat_model_start(self, serialized: Any, messages: Any, *, run_id: Any, **kwargs: Any) -> None:
        if any(count_tokens_approximately(batch, use_usage_metadata_scaling=False) > self.input_budget for batch in messages):
            raise ContextBudgetExceeded("摘要请求本身超过输入预算，原始历史未替换。请缩小工具返回或导入范围。")
        await _charge_call(self.context)
        await _emit(self.context, "model.call.started", {"call_id": str(run_id), "purpose": "summary"})

    async def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        for batch in response.generations:
            for generation in batch:
                message = getattr(generation, "message", None)
                info = {**(generation.generation_info or {}), **(getattr(message, "response_metadata", {}) or {})}
                reason = info.get("finish_reason") or info.get("stop_reason") or info.get("done_reason")
                self.truncated |= reason in {"length", "max_tokens", "max_output_tokens"}
                if usage := message_usage(message):
                    await _emit(self.context, "model.usage", {
                        "call_id": str(run_id), "purpose": "summary", "measurement": "provider", "usage": usage,
                    })

    async def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        self.error = error
        if self.model is not None and (receipt := capacity_from_error(error)):
            capacity, used = receipt
            if self.context is not None:
                self.context.context_capacity = capacity
            await _publish_context(self.context, self.model, capacity, self.configured, used,
                                   call_id=str(run_id), measurement="provider", purpose="summary")
        await _emit(self.context, "model.call.failed", {
            "call_id": str(run_id), "purpose": "summary", "error_type": type(error).__name__,
        })


class SafeSummarizationMiddleware(SummarizationMiddleware):
    """Use native selection/summary/checkpointing, but fail closed on data loss.

    LangChain can turn a failed summary request into an error-text summary.
    Do not commit that as a replacement for actual conversation history.
    System instructions remain outside the lossy summary.
    """

    def __init__(self, model: Any, *, input_budget: int, system_prompt: str = "", tools: list[Any] | None = None) -> None:
        super().__init__(model=model, trigger=("tokens", input_budget), trim_tokens_to_summarize=None)
        self.input_budget = input_budget
        self.system_prompt = system_prompt
        self.tools = []  # Do not register the supplied counting-only tools again.
        self.budget_tools = list(tools or [])

    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        if getattr(runtime.context, "direct_tool", None) is not None:
            # Explicit commands never need an LLM call, including summarization.
            return None
        # Refresh at every model turn, also after approvals/restarts. Load-time
        # settings can change without changing the model profile or graph key.
        capacity = await resolve_context_capacity(self.model, getattr(runtime.context, "context_capacity", None))
        if runtime.context is not None:
            runtime.context.context_capacity = capacity
        try:
            return await self._compact(state, runtime, capacity)
        except Exception as exc:
            await _emit(runtime.context, "context.compaction.failed", {
                "error_type": type(exc).__name__,
                "message": str(exc) if isinstance(exc, ContextBudgetExceeded) else "上下文压缩失败，原始历史未替换。",
                "reason": getattr(exc, "reason", ""),
                "model_context_window": (getattr(runtime.context, "context_capacity", None) or capacity).tokens,
            })
            raise

    async def _compact(
        self, state: Any, runtime: Any, capacity: ContextCapacity, *, force: bool = False,
        system_message: SystemMessage | None = None, request_tools: list[Any] | None = None,
    ) -> dict[str, Any] | None:
        messages = state["messages"]
        systems = [item for item in messages if isinstance(item, SystemMessage)]
        conversation = [item for item in messages if not isinstance(item, SystemMessage)]
        context = runtime.context
        enabled = getattr(context, "execution_metadata", {}).get("enabled_tools")
        tools = [tool for tool in self.budget_tools
                 if enabled is None or getattr(tool, "name", "") in {*enabled, "write_todos"}]
        if getattr(context, "max_subagent_calls", None) == 0:
            tools = [tool for tool in tools if getattr(tool, "name", "") not in {"delegate", "list_subagent_models"}]
        fixed = [*systems, *([SystemMessage(self.system_prompt)] if self.system_prompt else [])]
        if system_message is not None:
            fixed = [system_message]  # The wrapper already merged system instructions.
        if request_tools is not None:
            tools = request_tools
        overhead = count_tokens_approximately(fixed, tools=tools, use_usage_metadata_scaling=False)
        input_budget = effective_input_budget(self.model, self.input_budget, capacity)
        before = count_tokens_approximately(conversation, use_usage_metadata_scaling=False)
        # Publish even when compaction/admission fails before the model wrapper.
        await _publish_context(context, self.model, capacity, self.input_budget, before + overhead,
                               call_id=f"context_{uuid.uuid4().hex}")
        if capacity.tokens is None and not force:
            # A product default is not evidence of a deployment's window. Only
            # provider-confirmed overflow can force recovery without capacity.
            return None
        history_budget = input_budget - overhead
        if history_budget <= 0:
            raise ContextBudgetExceeded(
                f"当前模型的输入预算不足：固定指令和工具定义约 {overhead} tokens，"
                f"可用输入预算 {input_budget} tokens，尚未计入你的消息。"
                "这部分不能通过压缩聊天历史缩小；请减少启用的工具，或增大模型服务的实际加载窗口。",
                reason="fixed_overhead_exceeded",
            )
        if not force and before + overhead < int(input_budget * 0.8):
            return None
        target = max(1, min(int(input_budget * 0.10), 6000))
        upper = max(target, min(int(input_budget * 0.15), 8000))
        latest_index = next((i for i in range(len(conversation) - 1, -1, -1)
                             if isinstance(conversation[i], HumanMessage)), 0)
        protected_inputs: set[str] = set()
        if force and getattr(context, "adapter", None) is not None:
            pending = await context.adapter.repository.task_inputs(
                context.request.workspace_id, context.request.task_id, pending=True,
            )
            protected_inputs = {item["id"] for item in pending}
            latest_index = min([latest_index, *(i for i, item in enumerate(conversation)
                                               if item.id in protected_inputs)])
        # Keep the active user turn verbatim. Native middleware owns safe tool-pair
        # partitioning. There is no fixed post-compaction window-filling target.
        recent = max(count_tokens_approximately(conversation[latest_index:], use_usage_metadata_scaling=False), min(history_budget // 4, 8000), 1)
        if force:
            recent = max(count_tokens_approximately(conversation[latest_index:], use_usage_metadata_scaling=False), 1)
        observer = _SummaryObservation(context, input_budget, configured=self.input_budget)
        callbacks = self.model.callbacks
        if callbacks is None or isinstance(callbacks, list):
            callbacks = [*(callbacks or []), observer]
        else:
            callbacks = callbacks.copy()
            callbacks.add_handler(observer)
        # Overflow recovery runs inside the model node. Use LangGraph's public
        # no-stream tag so auxiliary summary text cannot become the UI answer.
        options: dict[str, Any] = {"callbacks": callbacks, "tags": [*(self.model.tags or []), TAG_NOSTREAM]}
        for field in ("max_tokens", "num_predict"):
            if field in type(self.model).model_fields:
                configured = getattr(self.model, field, None)
                limit = min(upper, configured) if isinstance(configured, int) and configured > 0 else upper
                options[field] = max(_minimum_output(self.model), limit)
                break
        # Public shallow model copy: only request options/callbacks change. HTTP
        # transports remain Core-owned and shared; no per-summary client creation.
        model = self.model.model_copy(update=options)
        observer.model = model
        observer.input_budget = effective_input_budget(model, self.input_budget, capacity)
        native = SummarizationMiddleware(
            model=model, trigger=("tokens", 1 if force else max(1, int(input_budget * 0.8) - overhead)),
            keep=("tokens", recent), trim_tokens_to_summarize=None,
            token_counter=lambda items: count_tokens_approximately(items, use_usage_metadata_scaling=False),
            summary_prompt=DEFAULT_SUMMARY_PROMPT + (
                f"\nAim for at most {target} tokens; never pad a short summary. Hard limit: {upper} tokens. "
                "Preserve the latest goal, explicit constraints, decisions, pending work and exact artifact paths. "
                "Distinguish verified actions from uncertain outcomes. Do not reproduce raw logs or reasoning. "
                "A summary is context, not permission to execute an action."
            ),
        )
        summary_state = dict(state)
        summary_state["messages"] = conversation
        await _emit(context, "context.compaction.started", {
            "before_tokens": before + overhead, "input_budget_tokens": input_budget,
            "model_context_window": capacity.tokens, "measurement": "estimate",
            "reason": "provider_overflow" if force else "pressure",
        })
        update = await native.abefore_model(cast(AgentState[Any], summary_state), runtime)
        if observer.error is not None:
            # Native summarization can swallow provider failures into text. Do
            # not mistake that for a successful checkpoint replacement.
            raise ContextBudgetExceeded("上下文压缩失败：摘要请求失败，原始历史未替换；请检查实际窗口和摘要输入大小。") from observer.error
        if update is None:
            await _emit(context, "context.compaction.skipped", {"reason": "no_compressible_history"})
            return None
        replacements = update["messages"]
        summary = replacements[1]
        if not isinstance(summary, HumanMessage):
            raise ContextBudgetExceeded("无法确认上下文摘要，原始上下文保留在 checkpoint。")
        text = summary.text.partition("\n\n")[2].strip()
        if not text or text.startswith(("Error generating summary:", "Previous conversation was too long")):
            raise ContextBudgetExceeded("上下文压缩失败，原始上下文保留在 checkpoint，请稍后重试。")
        if observer.truncated or count_tokens_approximately([HumanMessage(text)]) > upper:
            raise ContextBudgetExceeded("摘要被截断或超过长度上限，原始上下文未替换。")
        if count_tokens_approximately(replacements[1:], use_usage_metadata_scaling=False) >= before:
            raise ContextBudgetExceeded("压缩未能减少上下文，请缩小输入或工具返回范围。")
        retained = replacements[2:]
        latest_user = next((item for item in reversed(conversation) if isinstance(item, HumanMessage)), None)
        if latest_user is not None and not any(item.id == latest_user.id for item in retained):
            raise ContextBudgetExceeded("摘要没有保留当前用户回合，原始上下文未替换。")
        included_inputs = {item.id for item in conversation} & protected_inputs
        if not included_inputs.issubset({item.id for item in retained}):
            raise ContextBudgetExceeded("摘要没有保留待纳入的补充输入，原始上下文未替换。")
        after = count_tokens_approximately([summary, *retained], use_usage_metadata_scaling=False)
        if after + overhead > input_budget or after >= before:
            raise ContextBudgetExceeded("压缩后仍超过输入预算或未减少上下文，原始历史未替换。")
        await _emit(context, "context.compacted", {
            "measurement": "estimate", "before_tokens": before, "after_tokens": after,
            "summary_tokens": count_tokens_approximately([HumanMessage(text)]),
            "summary_target_tokens": target, "summary_limit_tokens": upper,
            "model_context_window": capacity.tokens, "input_budget_tokens": input_budget,
        })
        return {**update, "messages": [replacements[0], *systems, summary, *retained]}


class ContextBudgetMiddleware(AgentMiddleware):
    """Prepare one system prefix and reject oversized requests without losing history."""

    def __init__(self, max_tokens: int, summarizer: SafeSummarizationMiddleware | None = None) -> None:
        self.max_tokens = max_tokens
        self.summarizer = summarizer

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | ExtendedModelResponse:
        return await self._call(request, handler, allow_recovery=True)

    async def _call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]], *,
        allow_recovery: bool,
    ) -> ModelResponse | ExtendedModelResponse:
        # Recovery notices (including old checkpoints/imported history) are
        # system instructions in state. create_agent separately prepends its
        # system_message, so even consecutive systems break strict templates.
        # Project them into ONE prefix only for this call, before counting and
        # provider caching; leave checkpoint state and all other roles untouched.
        systems = [item for item in request.messages if isinstance(item, SystemMessage)]
        if systems:
            if request.system_message is not None:
                systems.insert(0, request.system_message)
            system = cast(SystemMessage, merge_message_runs(systems, chunk_separator="\n\n")[0])
            if isinstance(system.content, list):
                # TodoList uses content blocks; merging a plain recovery note
                # must not leave raw strings inside a provider's block array.
                system = system.model_copy(update={"content": [
                    {"type": "text", "text": block} if isinstance(block, str) else block
                    for block in system.content
                ]})
            request = request.override(
                system_message=system,
                messages=[item for item in request.messages if not isinstance(item, SystemMessage)],
            )
        messages = list(request.messages)
        if request.system_message is not None:
            messages.insert(0, request.system_message)
        # Historical usage describes the pre-compaction prompt. Scaling this
        # rewritten input by those counters would falsely reject a short summary.
        estimated = count_tokens_approximately(messages, tools=request.tools, use_usage_metadata_scaling=False)
        context: Any = request.runtime.context
        capacity = getattr(context, "context_capacity", None)
        # Parent compaction has just fetched the window. Children have no
        # summarizer, so resolve their own model rather than inheriting it.
        if capacity is None or getattr(context, "parent", None) is not None:
            capacity = await resolve_context_capacity(request.model, capacity)
            if context is not None:
                context.context_capacity = capacity
        input_budget = effective_input_budget(request.model, self.max_tokens, capacity)
        call_id = f"call_{uuid.uuid4().hex}"
        await _publish_context(context, request.model, capacity, self.max_tokens, estimated, call_id=call_id)
        if capacity.tokens is not None and estimated > input_budget:
            raise ContextBudgetExceeded(
                f"保留的请求约 {estimated} tokens，超过可用输入预算 {input_budget}；"
                "请缩小读取范围、减少工具，或增大模型服务的实际加载窗口。原始历史未丢弃。"
            )
        await _charge_call(context)
        await _emit(context, "model.call.started", {"call_id": call_id, "purpose": "response"})
        clock = _TokenClock()
        callbacks = request.model.callbacks
        if callbacks is None or isinstance(callbacks, list):
            callbacks = [*(callbacks or []), clock]
        else:
            callbacks = callbacks.copy()
            callbacks.add_handler(clock)
        # Public shallow copy keeps Core-owned HTTP clients shared and changes
        # only this invocation's callback list (also safe for concurrent sessions).
        options: dict[str, Any] = {"callbacks": callbacks}
        field = _output_field(request.model)
        reserve = _output_reserve(request.model, capacity)
        if field is not None and reserve:
            options[field] = reserve
        observed = request.model.model_copy(update=options)
        started_at = time.perf_counter()
        try:
            response = await handler(request.override(model=observed))
        except (Exception, asyncio.CancelledError) as exc:
            if receipt := capacity_from_error(exc):
                reported, used = receipt
                if context is not None:
                    context.context_capacity = reported
                await _publish_context(context, request.model, reported, self.max_tokens, used,
                                       call_id=call_id, measurement="provider")
            await _emit(context, "model.call.failed", {
                "call_id": call_id, "purpose": "response", "error_type": type(exc).__name__,
            })
            if (allow_recovery and self.summarizer is not None and not isinstance(exc, asyncio.CancelledError)
                    and is_context_overflow(exc) and clock.first_token_at is None):
                # Retry only a provider-confirmed rejection, before any visible
                # tokens. Native middleware selects safe pairs and creates the
                # replacement; public Command commits it with the final result.
                try:
                    update = await self.summarizer._compact(
                        request.state, request.runtime, getattr(context, "context_capacity", None) or capacity,
                        force=True, system_message=request.system_message, request_tools=request.tools,
                    )
                    if update is not None:
                        retry_messages = [item for item in update["messages"][1:]
                                          if not isinstance(item, SystemMessage)]
                        response = cast(ModelResponse, await self._call(
                            request.override(messages=retry_messages), handler, allow_recovery=False,
                        ))
                        return ExtendedModelResponse(
                            model_response=response,
                            command=Command(update={**update, "messages": [*update["messages"], *response.result]}),
                        )
                except Exception as recovery_error:
                    await _emit(context, "context.compaction.failed", {
                        "error_type": type(recovery_error).__name__,
                        "reason": getattr(recovery_error, "reason", ""),
                        "message": str(recovery_error) if isinstance(recovery_error, ContextBudgetExceeded)
                                   else "超限恢复失败，原始历史未替换。",
                    })
                    raise exc from recovery_error
            raise
        ended_at = time.perf_counter()
        timing = {
            "duration_ms": (ended_at - started_at) * 1000,
            "first_token_ms": (clock.first_token_at - started_at) * 1000 if clock.first_token_at else None,
            "decode_ms": (ended_at - clock.first_token_at) * 1000 if clock.first_token_at else None,
        }
        await _emit(context, "model.call.completed", {"call_id": call_id, "purpose": "response", **timing})
        for message in response.result:
            if isinstance(message, AIMessage) and (usage := message_usage(message)):
                await _emit(context, "model.usage", {
                    "call_id": call_id, "purpose": "response", "measurement": "provider", "usage": usage,
                    **timing,
                })
        return response
