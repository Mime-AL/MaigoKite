"""Context window management for LLM interactions."""

from __future__ import annotations

from typing import Any


class MessageChunk:
    """A single message chunk within the context window."""

    role: str
    content: str
    metadata: dict[str, Any]

    def __init__(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        ...


class ContextWindow:
    """Manages the LLM context window with sliding window semantics."""

    def __init__(self, max_tokens: int = 128000) -> None:
        ...

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        ...

    def trim_to_budget(self) -> None:
        ...

    def get_messages(self) -> list[MessageChunk]:
        ...

    @property
    def token_count(self) -> int:
        ...

    def clear(self) -> None:
        ...
