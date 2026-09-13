"""IChatProvider - Abstract interface for chat/completion LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
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
        ...


class ChatResponse:
    """Response from a chat provider."""

    content: str
    role: str
    usage: dict[str, int]
    finish_reason: str | None

    def __init__(
        self,
        content: str,
        role: str = "assistant",
        usage: dict[str, int] | None = None,
        finish_reason: str | None = None,
    ) -> None:
        ...


class IChatProvider(ABC):
    """Interface for LLM chat/completion providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        ...
    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Return an async iterator of response chunks."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
