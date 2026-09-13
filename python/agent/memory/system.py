"""IMemorySystem - Abstract interface for the unified memory system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IMemorySystem(ABC):
    """Abstract interface combining short-term, conversation, and user memory."""

    @abstractmethod
    async def save_short_term(self, key: str, value: Any) -> None:
        ...

    @abstractmethod
    async def retrieve_short_term(self, key: str) -> Any | None:
        ...

    @abstractmethod
    async def append_conversation(self, turn: dict[str, str]) -> None:
        ...

    @abstractmethod
    async def query_conversation(self, n: int) -> list[dict[str, str]]:
        ...

    @abstractmethod
    async def save_user_preference(self, key: str, value: Any) -> None:
        ...

    @abstractmethod
    async def get_user_preference(self, key: str) -> Any | None:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...
