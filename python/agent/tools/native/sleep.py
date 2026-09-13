"""SleepTool - Pause execution for a specified duration."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class SleepParams(BaseModel):
    """Parameters for pausing execution."""

    seconds: float = Field(
        description="Number of seconds to pause execution. Must be positive.",
        gt=0,
    )


def _sleep_impl(seconds: float) -> dict[str, Any]:
    """Pause execution for the specified number of seconds.

    Args:
        seconds: Duration in seconds to sleep.

    Returns:
        A dict with keys slept_seconds and timestamp.
    """
    start = time.monotonic()
    time.sleep(seconds)
    actual = time.monotonic() - start
    return {"slept_seconds": round(actual, 3), "timestamp": time.time()}


SLEEP_DESCRIPTION = (
    "Pause agent execution for a specified number of seconds. "
    "Useful for introducing delays between operations."
)


class SleepTool(BaseTool):
    """Pauses agent execution for a given duration via LangChain StructuredTool."""

    def __init__(self) -> None:
        self._structured = StructuredTool.from_function(
            func=_sleep_impl,
            name="sleep",
            description=SLEEP_DESCRIPTION,
            args_schema=SleepParams,
        )

    @property
    def name(self) -> str:
        return "sleep"

    @property
    def description(self) -> str:
        return self._structured.description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return SleepParams.model_json_schema()

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Execute the sleep operation."""
        result = _sleep_impl(**arguments)
        secs = result.get("slept_seconds", arguments.get("seconds", 0))
        return ToolResult(
            data={"slept_seconds": secs},
            summary=f"Slept for {secs:.1f} seconds",
            raw=f"slept {secs:.1f}s",
            metadata={"tool": "sleep", "type": "delay"},
        )
