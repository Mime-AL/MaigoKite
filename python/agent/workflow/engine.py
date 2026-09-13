"""LangGraph-based workflow engine for agent state machines."""

from __future__ import annotations

from typing import Any


class WorkflowState:
    """Shared state for the workflow graph."""

    messages: list[dict[str, str]]
    tools_used: list[str]
    memory_snapshot: dict[str, Any]
    metadata: dict[str, Any]

    def __init__(self) -> None:
        ...


class WorkflowEngine:
    """LangGraph-powered workflow engine for agent orchestration."""

    def __init__(self) -> None:
        ...

    def add_node(self, name: str, func: Any) -> None:
        """Add a node to the workflow graph."""
        ...

    def add_edge(self, source: str, target: str) -> None:
        """Add an edge between two nodes."""
        ...

    def add_conditional_edge(
        self, source: str, cond: Any, target_map: dict[str, str]
    ) -> None:
        """Add a conditional edge based on a predicate."""
        ...

    async def compile(self) -> Any:
        """Compile the workflow graph into an executable application."""
        ...

    async def run(self, initial_state: WorkflowState) -> WorkflowState:
        """Execute the workflow with the given initial state."""
        ...
