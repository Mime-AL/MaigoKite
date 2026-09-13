"""Short-term (working) memory backed by LangChain message chunks.

Keeps our custom sliding-window logic but represents messages as
LangChain ``BaseMessage`` objects instead of plain strings/dicts.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any

from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessageChunk, SystemMessageChunk

from agent.memory.short_term import IShortTermMemory


class ShortTermMemory(IShortTermMemory):
    """Transient, high-speed working memory using a sliding window.

    Messages are stored internally as lists of ``BaseMessage`` objects
    (``AIMessageChunk`` / ``HumanMessageChunk``).  The sliding-window
    policy keeps at most *window_size* recent message pairs; older ones
    are evicted on overflow.
    """

    def __init__(self, window_size: int = 50, ttl: int | None = None) -> None:
        self._window_size = window_size
        self._ttl = ttl
        # Ordered mapping: key -> list[BaseMessage]
        self._store: OrderedDict[str, list[BaseMessage]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Persist *value* under *key*, keeping it as a ``BaseMessage`` list.

        Args:
            key: Unique identifier for the entry.
            value: A ``BaseMessage`` or list/tuple of ``BaseMessage`` objects.
            ttl: Optional time-to-live in seconds (stored but enforcement is best-effort).
        """
        if isinstance(value, BaseMessage):
            msg_list: list[BaseMessage] = [value]
        elif isinstance(value, (list, tuple)):
            msg_list = list(value)
        else:
            msg_list = [value]

        await self._apply_sliding_window(key, msg_list)

    async def get(self, key: str) -> list[BaseMessage] | None:
        """Retrieve the full message list for *key*.

        Returns:
            A list of ``BaseMessage`` objects, or ``None`` if the key
            does not exist.
        """
        async with self._lock:
            msgs = self._store.get(key)
            return msgs.copy() if msgs else None

    async def delete(self, key: str) -> None:
        """Remove the entry identified by *key*.

        Args:
            key: Identifier of the entry to remove.
        """
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        """Remove all entries from short-term memory."""
        async with self._lock:
            self._store.clear()

    async def keys(self) -> list[str]:
        """Return all keys currently held in short-term memory.

        Returns:
            A list of string keys.
        """
        async with self._lock:
            return list(self._store.keys())

    # -- internal helpers --------------------------------------------------

    async def _apply_sliding_window(self, key: str, messages: list[BaseMessage]) -> None:
        """Enforce the sliding-window policy before storing.

        If an existing list is present, the new messages are appended.  When
        the total exceeds ``window_size``, the oldest messages are evicted so
        the stored list fits within the limit.
        """
        async with self._lock:
            existing = self._store.get(key, [])
            combined = existing + list(messages)

            if len(combined) > self._window_size:
                combined = combined[-self._window_size :]

            self._store[key] = combined
            self._store.move_to_end(key)
