"""FileReadTool - Read file contents using LangChain StructuredTool."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class FileReadParams(BaseModel):
    """Parameters for reading a file."""

    path: str = Field(description="Absolute or relative file path to read.")
    encoding: str = Field(default="utf-8", description="File encoding (default: utf-8).")
    max_bytes: int = Field(
        default=100_000,
        description="Maximum number of bytes to read (default: 100000).",
    )


def _file_read_impl(path: str, encoding: str = "utf-8", max_bytes: int = 100_000) -> dict[str, Any]:
    """Read file contents with a configurable size limit.

    Args:
        path: The file path to read.
        encoding: Character encoding of the file.
        max_bytes: Maximum number of characters to read.

    Returns:
        A dict with keys path, content, and size_bytes.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the process lacks read permission.
        UnicodeDecodeError: If the file cannot be decoded with the given encoding.
    """
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(abs_path, "r", encoding=encoding) as f:
        content = f.read(max_bytes)
    return {
        "path": path,
        "content": content,
        "size_bytes": len(content.encode(encoding)),
    }


FILE_READ_DESCRIPTION = (
    "Read the contents of a file at the given path. "
    "Supports reading text files with configurable encoding and size limits."
)


class FileReadTool(BaseTool):
    """Reads file contents from the filesystem via LangChain StructuredTool."""

    def __init__(self) -> None:
        self._structured = StructuredTool.from_function(
            func=_file_read_impl,
            name="file_read",
            description=FILE_READ_DESCRIPTION,
            args_schema=FileReadParams,
        )

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return self._structured.description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return FileReadParams.model_json_schema()

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Execute the file read operation and return structured results."""
        result = _file_read_impl(**arguments)
        content = result.get("content", "")
        size = result.get("size_bytes", len(content))
        read_path = result.get("path", arguments.get("path", ""))
        return ToolResult(
            data={"content": content, "path": read_path},
            summary=f"Read {size} bytes from {read_path}",
            raw=content,
            metadata={"tool": "file_read", "type": "text"},
        )
