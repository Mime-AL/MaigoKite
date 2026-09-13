"""BashTool - Execute shell commands safely using LangChain StructuredTool."""

from __future__ import annotations

import subprocess
import time
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class BashParams(BaseModel):
    """Parameters for executing a shell command."""

    command: str = Field(
        description=(
            "The shell command to execute. Run concise, targeted commands rather than "
            "long multi-step pipelines. Avoid commands that produce very large outputs."
        ),
    )
    timeout: int = Field(
        default=30,
        description="Maximum seconds to wait for the command before killing it (default: 30).",
    )
    workdir: str | None = Field(
        default=None,
        description=(
            "Working directory in which to run the command. "
            "If omitted, uses the current working directory."
        ),
    )


def _bash_impl(
    command: str,
    timeout: int = 30,
    workdir: str | None = None,
) -> dict[str, Any]:
    """Run a shell command and capture stdout, stderr, and exit code.

    Args:
        command: The command string to pass to the shell.
        timeout: Seconds before the process is killed.
        workdir: Optional working directory override.

    Returns:
        A dict with keys stdout, stderr, return_code, duration_seconds, and timed_out.
    """
    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir,
        )
        duration = time.monotonic() - start
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "return_code": proc.returncode,
            "duration_seconds": round(duration, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds.",
            "return_code": -1,
            "duration_seconds": round(duration, 3),
            "timed_out": True,
        }


BASH_DESCRIPTION = (
    "Execute a shell command in a sandboxed environment and return its output. "
    "Returns stdout, stderr, exit code, and execution duration."
)


class BashTool(BaseTool):
    """Executes shell commands via LangChain StructuredTool."""

    def __init__(self) -> None:
        self._structured = StructuredTool.from_function(
            func=_bash_impl,
            name="bash",
            description=BASH_DESCRIPTION,
            args_schema=BashParams,
        )

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return self._structured.description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return BashParams.model_json_schema()

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Run the shell command and wrap the result."""
        result = _bash_impl(**arguments)
        command = arguments.get("command", "")
        rc = result.get("return_code", -1)

        # Build a human-readable summary
        parts = [f"Exit code {rc}"]
        if result.get("timed_out"):
            parts.insert(0, "Timed out")
        if result.get("stdout"):
            summary_len = min(len(result["stdout"]), 200)
            parts.append(f"stdout: {result['stdout'][:summary_len]}")
        if result.get("stderr"):
            summary_len = min(len(result["stderr"]), 200)
            parts.append(f"stderr: {result['stderr'][:summary_len]}")
        parts.append(f"Duration: {result.get('duration_seconds', 0):.2f}s")

        return ToolResult(
            data={
                "return_code": rc,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "duration_seconds": result["duration_seconds"],
                "timed_out": result.get("timed_out", False),
            },
            summary="; ".join(parts),
            raw=result["stdout"] or result["stderr"] or "",
            metadata={"tool": "bash", "type": "shell", "exit_code": rc},
        )
