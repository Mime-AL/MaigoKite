"""Observability: logging, tracing, and metrics for the agent core."""

from __future__ import annotations

from typing import Any


class Observer:
    """Base interface for an observability observer."""

    async def on_event(self, event_type: str, data: dict[str, Any]) -> None:
        ...

    async def on_metric(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        ...

    async def on_trace(self, trace_id: str, span_data: dict[str, Any]) -> None:
        ...


class ConsoleObserver(Observer):
    """Phase 1 observer that writes to stdout."""

    async def on_event(self, event_type: str, data: dict[str, Any]) -> None:
        ...

    async def on_metric(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        ...

    async def on_trace(self, trace_id: str, span_data: dict[str, Any]) -> None:
        ...


class Observability:
    """Central observability hub for logs, traces, and metrics."""

    def __init__(self) -> None:
        ...

    def add_observer(self, observer: Observer) -> None:
        ...

    async def log(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        ...

    async def trace(self, trace_id: str, operation: str, data: dict[str, Any] | None = None) -> None:
        ...

    async def metric(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        ...
