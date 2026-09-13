"""In-memory event bus for inter-component communication."""

from __future__ import annotations

from typing import Any, Callable, Coroutine


EventCallback = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """In-memory publish/subscribe event bus."""

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        """Register a callback for an event type."""
        ...

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        """Remove a callback for an event type."""
        ...

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        ...

    def clear(self) -> None:
        """Remove all subscriptions."""
        ...
