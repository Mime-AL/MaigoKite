"""In-process task lifecycle manager."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    COMPLETED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentTask:
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    parent_task_id: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, AgentTask] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, title: str, description: str, parent_id: str | None = None, *, task_id: str = "") -> AgentTask:
        task = AgentTask(task_id or f"task_{uuid.uuid4().hex}", title, description, parent_task_id=parent_id)
        async with self._lock:
            if parent_id and parent_id not in self._tasks:
                raise KeyError(f"parent task not found: {parent_id}")
            self._tasks[task.id] = task
        return task

    async def update_status(self, task_id: str, status: TaskStatus) -> None:
        async with self._lock:
            task = self._require(task_id)
            task.status = status
            task.updated_at = _now()

    async def get_task(self, task_id: str) -> AgentTask | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def list_tasks(self, status: TaskStatus | None = None) -> list[AgentTask]:
        async with self._lock:
            return [task for task in self._tasks.values() if status is None or task.status == status]

    async def cancel_task(self, task_id: str) -> None:
        await self.update_status(task_id, TaskStatus.CANCELLED)

    async def complete_task(self, task_id: str, result: dict[str, Any]) -> None:
        async with self._lock:
            task = self._require(task_id)
            task.status = TaskStatus.SUCCEEDED
            task.metadata["result"] = result
            task.updated_at = _now()

    def _require(self, task_id: str) -> AgentTask:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task not found: {task_id}")
        return task
