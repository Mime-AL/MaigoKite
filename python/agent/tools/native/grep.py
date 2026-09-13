"""GrepTool - Search file contents with regex using LangChain StructuredTool."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class GrepParams(BaseModel):
    """Parameters for searching file contents."""

    pattern: str = Field(
        description="A Python regular expression to search for within file contents.",
    )
    path: str = Field(
        default=".",
        description=(
            "File or directory path to search within. "
            "If a directory, searches recursively."
        ),
    )
    ignore_case: bool = Field(
        default=False,
        description="Perform case-insensitive matching (default: False).",
    )
    max_results: int = Field(
        default=100,
        description="Maximum number of matches to return (default: 100).",
    )
    context_lines: int = Field(
        default=0,
        description="Number of context lines before and after each match (default: 0).",
    )


def _grep_impl(
    pattern: str,
    path: str = ".",
    ignore_case: bool = False,
    max_results: int = 100,
    context_lines: int = 0,
) -> dict[str, Any]:
    """Search file contents using a regular expression.

    Recursively walks directories and reads files, collecting matches
    with optional context lines. Skips binary files silently.

    Args:
        pattern: Regular expression pattern.
        path: Root file or directory to search.
        ignore_case: Enable case-insensitive matching.
        max_results: Upper bound on returned matches.
        context_lines: Number of surrounding lines per match.

    Returns:
        A dict with keys matches (list of hit dicts) and total_count.
    """
    flags = re.IGNORECASE if ignore_case else 0
    compiled = re.compile(pattern, flags)

    root = Path(path).resolve()
    hits: list[dict[str, Any]] = []
    file_hits: list[tuple[int, int, int]] = []  # (file_idx, line_number, context_range)
    current_match = 0
    total_files_scanned = 0

    def _process_file(file_path: Path) -> None:
        nonlocal current_match
        if current_match >= max_results:
            return
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return
        total_files_scanned = 0  # workaround: track below instead
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if current_match >= max_results:
                return
            if compiled.search(line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + 1 + context_lines)
                context = "\n".join(lines[start:end])
                hits.append({
                    "file": str(file_path.relative_to(root)),
                    "line_number": i + 1,
                    "context": context,
                })
                current_match += 1

    if not root.exists():
        return {"matches": [], "total_count": 0, "files_scanned": 0}

    if root.is_file():
        _process_file(root)
        total_files_scanned = 1
    elif root.is_dir():
        all_files: list[Path] = []
        for entry in sorted(root.rglob("*")):
            if entry.is_file():
                all_files.append(entry)
                if len(all_files) > 5000:
                    break
        total_files_scanned = len(all_files)
        for f in all_files:
            if current_match >= max_results:
                break
            _process_file(f)

    return {
        "matches": hits,
        "total_count": current_match,
        "files_scanned": total_files_scanned,
    }


GREP_DESCRIPTION = (
    "Search file contents using a regular expression. "
    "Can search a single file or recursively through a directory. "
    "Returns matched lines with context."
)


class GrepTool(BaseTool):
    """Searches file contents using regex via LangChain StructuredTool."""

    def __init__(self) -> None:
        self._structured = StructuredTool.from_function(
            func=_grep_impl,
            name="grep",
            description=GREP_DESCRIPTION,
            args_schema=GrepParams,
        )

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return self._structured.description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return GrepParams.model_json_schema()

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Run the regex search and format results."""
        result = _grep_impl(**arguments)
        pattern = arguments.get("pattern", "")
        matches = result.get("matches", [])
        formatted = []
        for h in matches:
            formatted.append(f"{h['file']}:{h['line_number']}:\n{h['context']}")
        raw_output = "\n---\n".join(formatted) if formatted else ""
        return ToolResult(
            data={
                "pattern": pattern,
                "matches": matches,
                "total_count": result["total_count"],
                "files_scanned": result["files_scanned"],
            },
            summary=f"Found {result['total_count']} match(es) in {result['files_scanned']} file(s)",
            raw=raw_output,
            metadata={"tool": "grep", "type": "search"},
        )
