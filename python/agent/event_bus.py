"""Small asynchronous event bus used inside Agent Core."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

EventCallback = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[EventCallback]] = defaultdict(set)
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        self._subscribers[event_type].add(callback)

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        callbacks = self._subscribers.get(event_type)
        if callbacks:
            callbacks.discard(callback)
            if not callbacks:
                self._subscribers.pop(event_type, None)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            callbacks = tuple(self._subscribers.get(event_type, ())) + tuple(
                self._subscribers.get("*", ())
            )
        if callbacks:
            await asyncio.gather(*(cb(event_type, payload) for cb in callbacks))

    def clear(self) -> None:
        self._subscribers.clear()
