"""Bounded in-process working memory used to assemble model context."""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any


class ShortTermMemory:
    def __init__(self, window_size: int = 50, ttl: int | None = None) -> None:
        if window_size < 1:
            raise ValueError("window_size must be positive")
        self._window_size = window_size
        self._default_ttl = ttl
        self._store: OrderedDict[str, tuple[Any, float | None]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        lifetime = self._default_ttl if ttl is None else ttl
        expires_at = None if lifetime is None else time.monotonic() + lifetime
        async with self._lock:
            self._store[key] = (value, expires_at)
            self._store.move_to_end(key)
            while len(self._store) > self._window_size:
                self._store.popitem(last=False)

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and time.monotonic() >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def keys(self) -> list[str]:
        async with self._lock:
            now = time.monotonic()
            expired = [key for key, (_, expiry) in self._store.items() if expiry is not None and now >= expiry]
            for key in expired:
                self._store.pop(key, None)
            return list(self._store)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
