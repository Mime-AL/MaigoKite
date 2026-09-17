"""IChatProvider - Abstract interface for chat/completion LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from collections.abc import AsyncIterator


class ChatMessage:
    """A single chat message."""

    role: str
    content: str
    metadata: dict[str, Any]

    def __init__(
        self, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        if role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"unsupported chat role: {role}")
        self.role = role
        self.content = content
        self.metadata = metadata or {}


class ChatResponse:
    """Response from a chat provider."""

    content: str
    role: str
    usage: dict[str, int]
    finish_reason: str | None
    tool_calls: list[ToolCall]

    def __init__(
        self,
        content: str,
        role: str = "assistant",
        usage: dict[str, int] | None = None,
        finish_reason: str | None = None,
        tool_calls: list[ToolCall] | None = None,
    ) -> None:
        self.content = content
        self.role = role
        self.usage = usage or {}
        self.finish_reason = finish_reason
        self.tool_calls = tool_calls or []


@dataclass(slots=True)
class ToolCall:
    """Provider-neutral model request to invoke a registered tool."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolCallChunk:
    """A possibly-fragmented tool call emitted by a streaming provider."""

    index: int
    id: str = ""
    name: str = ""
    arguments: str = ""


@dataclass(slots=True)
class ChatStreamChunk:
    """Normalized token/tool-call delta emitted by every chat provider."""

    content: str = ""
    reasoning: str = ""
    tool_call_chunks: list[ToolCallChunk] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class IChatProvider(ABC):
    """Interface for LLM chat/completion providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        ...
    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatStreamChunk]:
        """Return normalized response and tool-call deltas."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
