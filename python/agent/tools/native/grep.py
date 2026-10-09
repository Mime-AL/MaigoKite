"""Read-only content search using ripgrep, not a second regex/search engine."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult
from agent.utils.sandbox import SandboxExecutor


class GrepParams(BaseModel):
    pattern: str = Field(min_length=1, description="Ripgrep (Rust regex) pattern, not Python regex.")
    path: str = Field(default=".", description="Workspace file or directory to search.")
    ignore_case: bool = False
    max_results: int = Field(default=100, ge=1, le=1000)
    context_lines: int = Field(default=0, ge=0, le=20)


class GrepTool(BaseTool):
    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search text with ripgrep. Respects ignore files, skips hidden/binary files and does not follow symlinks."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return GrepParams.model_json_schema()

    async def execute(self, context: ExecutionContext, arguments: dict[str, Any]) -> ToolResult:
        args = GrepParams.model_validate(arguments)
        target = Path(args.path).resolve()
        root = target if target.is_dir() else target.parent
        executor = SandboxExecutor({
            "workspace_root": context.metadata.get("workspace_root", str(root)), "workdir": str(root),
        })
        command = ["rg", "--no-config", "--json", "--sort", "path", "--context", str(args.context_lines)]
        if args.ignore_case:
            command.append("--ignore-case")
        command.extend(["--", args.pattern, "." if target.is_dir() else str(target)])
        try:
            result = await executor.execute_command(shlex.join(command))
        except FileNotFoundError:
            return ToolResult.failure({}, "ripgrep is not installed.", error_code="RIPGREP_UNAVAILABLE",
                                      user_hint="文件搜索需要 ripgrep（rg），请安装后重试。")
        if result.timed_out or result.exit_code not in {0, 1}:
            return ToolResult.failure({}, result.stderr or "Content search failed.", error_code="FILE_SEARCH_FAILED")
        matches: list[tuple[str, int]] = []
        lines: dict[str, dict[int, str]] = {}
        files_scanned = 0
        for row in result.stdout.splitlines():
            try:
                event = json.loads(row)
            except json.JSONDecodeError:
                if result.output_truncated:
                    break
                raise
            data = event.get("data", {})
            if event.get("type") == "summary":
                files_scanned = int(data.get("stats", {}).get("searches", 0))
            if event.get("type") not in {"match", "context"}:
                continue
            path = data.get("path", {}).get("text")
            text = data.get("lines", {}).get("text")
            if not isinstance(path, str) or not isinstance(text, str):
                continue
            filename = str(Path(path).relative_to(root)) if Path(path).is_absolute() else path.removeprefix("./")
            number = int(data["line_number"])
            lines.setdefault(filename, {})[number] = text.rstrip("\r\n")
            if event["type"] == "match":
                matches.append((filename, number))
        hits = [
            {"file": path, "line_number": number, "context": "\n".join(
                lines[path][line] for line in range(max(1, number - args.context_lines), number + args.context_lines + 1)
                if line in lines[path]
            )}
            for path, number in matches[:args.max_results]
        ]
        truncated = result.output_truncated or len(matches) > args.max_results
        return ToolResult(
            {"pattern": args.pattern, "matches": hits, "total_count": len(hits),
             "files_scanned": files_scanned, "truncated": truncated},
            f"Found {len(hits)} match(es)" + (" (truncated)" if truncated else ""),
            raw="\n".join(f"{hit['file']}:{hit['line_number']}: {hit['context']}" for hit in hits),
        )
