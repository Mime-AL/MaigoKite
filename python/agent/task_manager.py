"""Task management for the agent core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """Represents a single task in the agent lifecycle."""

    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    parent_task_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """Manages creation, tracking, and lifecycle of agent tasks."""

    def __init__(self) -> None:
        ...

    async def create_task(
        self, title: str, description: str, parent_id: Optional[str] = None
    ) -> AgentTask:
        ...

    async def update_status(self, task_id: str, status: TaskStatus) -> None:
        ...

    async def get_task(self, task_id: str) -> AgentTask | None:
        ...

    async def list_tasks(self, status: Optional[TaskStatus] = None) -> list[AgentTask]:
        ...

    async def cancel_task(self, task_id: str) -> None:
        ...

    async def complete_task(self, task_id: str, result: dict[str, Any]) -> None:
        ...
