"""Execution engine for running agent steps and tool invocations."""

from __future__ import annotations
import json
from datetime import datetime
from typing import Any, Optional


class ExecutionContext:
    """Context passed to tool executions."""

    deadline: datetime
    cancellation_token: bool
    trace_id: str
    task_id: str
    step_id: str
    metadata: dict[str, Any]

    def __init__(
        self,
        trace_id: str,
        task_id: str,
        step_id: str,
        deadline: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...


class ToolResult:
    """Standardized result returned by tool executions."""

    data: dict[str, Any]
    summary: str
    raw: str | bytes | None
    metadata: dict[str, Any]

    def __init__(
        self,
        data: dict[str, Any],
        summary: str,
        raw: str | bytes | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...


class ToolResultStream:
    """Streaming variant of ToolResult for long-running operations."""

    def __aiter__(self) -> Any:
        ...

    async def collect(self) -> ToolResult:
        ...


class ExecutionEngine:
    """Executes agent steps and manages tool invocations."""

    def __init__(self, trace_id: str, task_id: str) -> None:
        ...

    async def execute_step(
        self, step_config: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        ...

    async def execute_tool(
        self, tool_name: str, arguments: dict[str, Any], context: ExecutionContext
    ) -> ToolResult | ToolResultStream:
        ...

    async def cancel(self) -> None:
        ...
