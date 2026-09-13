"""Sandbox utilities for safe code and command execution."""

from __future__ import annotations

from typing import Any


class SandboxExecutionResult:
    """Result of a sandboxed execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float

    def __init__(
        self,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        duration_ms: float = 0.0,
    ) -> None:
        ...


class SandboxExecutor:
    """Provides sandboxed execution environments."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        ...

    async def execute_command(
        self, command: str, timeout: int = 30
    ) -> SandboxExecutionResult:
        ...

    async def execute_python(
        self, code: str, timeout: int = 30
    ) -> SandboxExecutionResult:
        ...

    def set_limits(self, cpu_seconds: float, memory_mb: int) -> None:
        ...
