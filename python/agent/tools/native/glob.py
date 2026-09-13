"""GlobTool - Find files matching glob patterns using LangChain StructuredTool."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class GlobParams(BaseModel):
    """Parameters for glob pattern matching."""

    pattern: str = Field(
        description=(
            "A glob / filename-matching pattern (e.g., '**/*.py', 'src/**/*.rs'). "
            "Uses Python fnmatch-style syntax."
        ),
    )
    root_dir: str = Field(
        default=".",
        description="Root directory from which to begin searching (default: current directory).",
    )


def _glob_impl(pattern: str, root_dir: str = ".") -> dict[str, Any]:
    """Recursively find files matching a glob-style pattern.

    Args:
        pattern: The glob pattern to match against file names.
        root_dir: Directory tree root for the search.

    Returns:
        A dict with keys matches (sorted list of paths) and count.
    """
    root = Path(root_dir).resolve()
    matches: list[str] = []
    if not root.is_dir():
        return {"matches": [], "count": 0}

    for entry in root.rglob("*"):
        if entry.is_file() and fnmatch(entry.name, pattern):
            matches.append(str(entry.relative_to(root)))

    matches.sort()
    return {"matches": matches, "count": len(matches)}


GLOB_DESCRIPTION = (
    "Recursively find files matching a glob pattern within a directory tree. "
    "Returns a sorted list of matched file paths relative to the root directory."
)


class GlobTool(BaseTool):
    """Finds files matching a glob pattern via LangChain StructuredTool."""

    def __init__(self) -> None:
        self._structured = StructuredTool.from_function(
            func=_glob_impl,
            name="glob",
            description=GLOB_DESCRIPTION,
            args_schema=GlobParams,
        )

    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return self._structured.description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return GlobParams.model_json_schema()

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Execute the glob search and return matching paths."""
        result = _glob_impl(**arguments)
        pattern = arguments.get("pattern", "")
        matches = result.get("matches", [])
        return ToolResult(
            data={"pattern": pattern, "matches": matches, "count": result["count"]},
            summary=f"Found {result['count']} file(s) matching '{pattern}'",
            raw="\n".join(matches),
            metadata={"tool": "glob", "type": "file_list"},
        )
