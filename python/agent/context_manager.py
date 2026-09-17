"""Context-window management with deterministic trimming."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


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
        while len(self._messages) > 1 and self.token_count > self.max_tokens:
            self._messages.pop(1 if self._messages[0].role == "system" else 0)
        if self._messages and self.token_count > self.max_tokens:
            self._messages[-1].content = self._messages[-1].content[-self.max_tokens * 4 :]

    def get_messages(self) -> list[MessageChunk]:
        return list(self._messages)

    @property
    def token_count(self) -> int:
        return sum(_estimate_tokens(message.content) for message in self._messages)

    def clear(self) -> None:
        self._messages.clear()


class ContextManager(ContextWindow):
    pass
