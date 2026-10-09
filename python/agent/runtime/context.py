"""Small product safety guards around LangChain's context middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, SummarizationMiddleware
from langchain.agents.middleware.types import AgentState, ModelRequest, ModelResponse
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately

from agent.context_manager import ContextBudgetExceeded


class SafeSummarizationMiddleware(SummarizationMiddleware):
    """Use native selection/summary/checkpointing, but fail closed on data loss.

    LangChain can turn a failed summary request into an error-text summary.
    Do not commit that as a replacement for actual conversation history.
    System instructions remain outside the lossy summary.
    """

    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        messages = state["messages"]
        systems = [item for item in messages if isinstance(item, SystemMessage)]
        conversation = [item for item in messages if not isinstance(item, SystemMessage)]
        summary_state = dict(state)
        summary_state["messages"] = conversation
        update = await super().abefore_model(cast(AgentState[Any], summary_state), runtime)
        if update is None:
            return None
        replacements = update["messages"]
        summary = replacements[1]
        if not isinstance(summary, HumanMessage):
            raise ContextBudgetExceeded("无法确认上下文摘要，原始上下文保留在 checkpoint。")
        text = summary.text.partition("\n\n")[2].strip()
        if not text or text.startswith(("Error generating summary:", "Previous conversation was too long")):
            raise ContextBudgetExceeded("上下文压缩失败，原始上下文保留在 checkpoint，请稍后重试。")
        if count_tokens_approximately(replacements[1:]) >= count_tokens_approximately(conversation):
            raise ContextBudgetExceeded("压缩未能减少上下文，请缩小输入或工具返回范围。")
        retained = replacements[2:]
        latest_user = next((item for item in reversed(conversation) if isinstance(item, HumanMessage)), None)
        if latest_user is not None and not any(item.id == latest_user.id for item in retained):
            retained = [latest_user, *retained]
        return {**update, "messages": [replacements[0], *systems, summary, *retained]}


class ContextBudgetMiddleware(AgentMiddleware):
    """Reject an oversized retained request rather than repeatedly summarizing it."""

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        messages = list(request.messages)
        if request.system_message is not None:
            messages.insert(0, request.system_message)
        # Historical usage describes the pre-compaction prompt. Scaling this
        # rewritten input by those counters would falsely reject a short summary.
        if count_tokens_approximately(messages, tools=request.tools) > self.max_tokens:
            raise ContextBudgetExceeded("保留的请求或工具结果超过上下文输入预算，请缩小读取范围或拆分任务。")
        return await handler(request)
