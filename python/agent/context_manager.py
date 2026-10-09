"""Bound legacy request context with LangChain's message-aware utilities.

This is a request projection, not a second conversation store. Never truncate
the user's current turn or split tool calls from their results to make it fit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from agent.models.chat_adapter import ChatAdapter
from agent.models.chat_provider import ChatMessage


class ContextBudgetExceeded(ValueError):
    """A request needs smaller inputs, not silent loss of its instructions."""


@dataclass
class MessageChunk:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"unsupported message role: {self.role}")


class ContextWindow:
    def __init__(self, max_tokens: int = 128000) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        self.max_tokens = max_tokens
        self._messages: list[MessageChunk] = []

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._messages.append(MessageChunk(role, content, metadata or {}))
        self.trim_to_budget()

    def trim_to_budget(self) -> None:
        selected = self.prepare([ChatMessage(item.role, item.content, item.metadata) for item in self._messages])
        self._messages = [MessageChunk(item.role, item.content, item.metadata) for item in selected]

    def prepare(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> list[ChatMessage]:
        """Keep a stable prefix until pressure, then retain whole recent turns.

        The budget includes tool schemas and message overhead. It is an input
        budget (not the provider's context-window size); counts are estimates.
        """
        native = ChatAdapter.to_langchain_messages(messages)
        schema_tools: list[BaseTool | dict[str, Any]] = list(tools or [])

        def count(items: list[BaseMessage]) -> int:
            return count_tokens_approximately(items, tools=schema_tools)

        if count(native) <= self.max_tokens:
            return list(messages)
        for index, message in enumerate(native):
            message.id = str(index)
        selected = trim_messages(
            native,
            max_tokens=self.max_tokens,
            token_counter=count,
            strategy="last",
            start_on="human",
            include_system=True,
            allow_partial=False,
        )
        indices = {int(message.id) for message in selected if message.id is not None}
        latest_user = next(
            (index for index in range(len(messages) - 1, -1, -1) if messages[index].role == "user"),
            0,
        )
        if not set(range(latest_user, len(messages))).issubset(indices) or count(selected) > self.max_tokens:
            raise ContextBudgetExceeded(
                "当前请求或工具结果超过上下文输入预算，请缩小文件读取范围、拆分任务，"
                "或按模型实际容量调整 context.max_tokens；原始记录未被修改。"
            )
        return [messages[int(message.id)] for message in selected if message.id is not None]

    def get_messages(self) -> list[MessageChunk]:
        return list(self._messages)

    @property
    def token_count(self) -> int:
        return count_tokens_approximately(
            ChatAdapter.to_langchain_messages(
                [ChatMessage(item.role, item.content, item.metadata) for item in self._messages]
            )
        )

    def clear(self) -> None:
        self._messages.clear()


class ContextManager(ContextWindow):
    pass
