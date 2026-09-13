"""Timeline builder for reconstructing agent execution history."""

from __future__ import annotations

from typing import Any

from agent.inspector.events import InspectorEvent


class TimelineEntry:
    """A single entry in the execution timeline."""

    event: InspectorEvent
    position: int

    def __init__(self, event: InspectorEvent, position: int) -> None:
        ...


class TimelineBuilder:
    """Builds and manages the chronological execution timeline."""

    def __init__(self, trace_id: str) -> None:
        ...

    def append(self, event: InspectorEvent) -> None:
        ...

    def get_entries(self) -> list[TimelineEntry]:
        ...

    def filter_by_type(self, event_type: str) -> list[TimelineEntry]:
        ...

    def filter_by_task(self, task_id: str) -> list[TimelineEntry]:
        ...

    def export_json(self) -> dict[str, Any]:
        ...
