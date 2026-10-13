"""Test-only fault injection around the real Core/file tool; never shipped as an API."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from agent.main import main_cli
from agent.tools.base import ExecutionContext, ToolResult
from agent.tools.native.file_write import FileWriteTool


def main() -> None:
    root = Path(os.environ["MAIGOKITE_WORKSPACE_ROOT"])
    barrier = os.environ.get("MAIGOKITE_TEST_WRITE_BARRIER", "")
    original_execute = FileWriteTool.execute

    async def pause() -> None:
        (root / "write-barrier").write_text(barrier, encoding="utf-8")
        await asyncio.Event().wait()  # Parent kills this process, no graceful cleanup.

    async def execute(self: FileWriteTool, context: ExecutionContext, arguments: dict[str, Any]) -> ToolResult:
        if barrier == "before":
            await pause()
        result = await original_execute(self, context, arguments)
        with (root / "write-receipts").open("a", encoding="utf-8") as receipt:
            receipt.write(f"{int(result.data['bytes_written'])}\n")
        if barrier == "after":
            await pause()  # Actual write finished, but no ToolMessage/result checkpoint.
        return result

    FileWriteTool.execute = execute
    main_cli()


if __name__ == "__main__":
    main()
