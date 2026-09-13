"""Sub-agent management for hierarchical agent execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


class SubAgentSpec:
    """Specification for a sub-agent instance."""

    agent_id: str
    name: str
    role: str
    instructions: str
    parent_task_id: str
    created_at: datetime

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        instructions: str,
        parent_task_id: str,
    ) -> None:
        ...


class SubAgentManager:
    """Manages creation, lifecycle, and coordination of sub-agents."""

    def __init__(self, parent_context: dict[str, Any]) -> None:
        ...

    async def spawn(self, spec: SubAgentSpec) -> str:
        """Spawn a sub-agent and return its agent_id."""
        ...

    async def await_completion(self, agent_id: str) -> dict[str, Any]:
        """Wait for a sub-agent to complete and return results."""
        ...

    async def cancel(self, agent_id: str) -> None:
        """Cancel a running sub-agent."""
        ...

    async def list_active(self) -> list[str]:
        """Return IDs of currently active sub-agents."""
        ...
