"""AgentCore - Main orchestrator class for the NanamiGopher agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from agent.task_manager import TaskManager
from agent.execution_engine import ExecutionEngine
from agent.skill_registry import SkillRegistry
from agent.sub_agent_manager import SubAgentManager
from agent.context_manager import ContextManager
from agent.config_manager import ConfigManager
from agent.event_bus import EventBus
from agent.recovery import ExecutionRecovery
from agent.observability import Observability


class AgentCore:
    """Main orchestrator that coordinates all agent subsystems."""

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        observability: Observability,
    ) -> None:
        ...

    async def initialize(self) -> None:
        """Initialize all subsystems."""
        ...

    async def shutdown(self) -> None:
        """Gracefully shut down all subsystems."""
        ...

    async def run(self, prompt: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the agent loop with the given prompt."""
        ...

    async def interrupt(self) -> None:
        """Request interruption of the current execution."""
        ...

    @property
    def task_manager(self) -> TaskManager:
        ...

    @property
    def execution_engine(self) -> ExecutionEngine:
        ...

    @property
    def skill_registry(self) -> SkillRegistry:
        ...

    @property
    def sub_agent_manager(self) -> SubAgentManager:
        ...

    @property
    def context_manager(self) -> ContextManager:
        ...
