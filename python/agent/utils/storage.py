"""Storage abstraction for persistent agent data."""

from __future__ import annotations

from typing import Any


class StorageBackend:
    """Abstract interface for a storage backend."""

    async def get(self, key: str) -> Any | None:
        ...

    async def set(self, key: str, value: Any) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def keys(self, prefix: str = "") -> list[str]:
        ...

    async def clear(self) -> None:
        ...


class FileStorage(StorageBackend):
    """File-system backed storage implementation."""

    async def get(self, key: str) -> Any | None:
        ...

    async def set(self, key: str, value: Any) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def keys(self, prefix: str = "") -> list[str]:
        ...

    async def clear(self) -> None:
        ...


class MemoryStorage(StorageBackend):
    """In-memory storage implementation for testing and ephemeral use."""

    async def get(self, key: str) -> Any | None:
        ...

    async def set(self, key: str, value: Any) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def keys(self, prefix: str = "") -> list[str]:
        ...

    async def clear(self) -> None:
        ...
