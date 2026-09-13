"""TodoWriteTool - Manage a TODO list via LangChain StructuredTool."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult

# Module-level mutable state for the TODO list.
# In production this would be backed by a database or context metadata.
_todo_items: list[dict[str, Any]] = []


class TodoWriteParams(BaseModel):
    """Parameters for managing a TODO list."""

    operation: str = Field(
        description="Operation to perform: 'add', 'update', 'list', or 'clear'.",
        pattern=r"^(add|update|list|clear)$",
    )
    text: str | None = Field(
        default=None,
        description="Description text for the todo item (required for add/update).",
    )
    index: int | None = Field(
        default=None,
        description="Index of the item to update (0-based, required for update).",
    )


def _todo_write_impl(
    operation: str,
    text: str | None = None,
    index: int | None = None,
) -> dict[str, Any]:
    """Add, update, list, or clear TODO items.

    Args:
        operation: One of 'add', 'update', 'list', 'clear'.
        text: Description text for add/update operations.
        index: Zero-based index for update operations.

    Returns:
        A dict with keys operation, items (list of todos), and count.
    """
    global _todo_items

    if operation == "add":
        if not text:
            raise ValueError("'text' is required for 'add' operation")
        _todo_items.append({"id": len(_todo_items), "text": text, "done": False})
    elif operation == "update":
        if index is None or text is None:
            raise ValueError("'index' and 'text' are required for 'update' operation")
        if index < 0 or index >= len(_todo_items):
            raise IndexError(f"Index {index} out of range (list has {len(_todo_items)} items)")
        _todo_items[index]["text"] = text
    elif operation == "list":
        pass  # just return current state
    elif operation == "clear":
        _todo_items.clear()
    else:
        raise ValueError(f"Unknown operation: {operation}")

    return {
        "operation": operation,
        "items": list(_todo_items),
        "count": len(_todo_items),
    }


TODO_DESCRIPTION = (
    "Manage a TODO list with add, update, list, and clear operations. "
    "Useful for tracking multi-step tasks during agent execution."
)


class TodoWriteTool(BaseTool):
    """Manages a TODO list via LangChain StructuredTool."""

    def __init__(self) -> None:
        self._structured = StructuredTool.from_function(
            func=_todo_write_impl,
            name="todo_write",
            description=TODO_DESCRIPTION,
            args_schema=TodoWriteParams,
        )

    @property
    def name(self) -> str:
        return "todo_write"

    @property
    def description(self) -> str:
        return self._structured.description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return TodoWriteParams.model_json_schema()

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        """Execute the TODO operation and return results."""
        result = _todo_write_impl(**arguments)
        op = result.get("operation", "")
        items = result.get("items", [])
        if op == "list":
            summary = f"{len(items)} item(s) in TODO list"
        elif op == "add":
            summary = f"Added item: {items[-1]['text'] if items else ''}"
        elif op == "update":
            idx = arguments.get("index", 0)
            summary = f"Updated item {idx}: {items[idx]['text'] if idx < len(items) else ''}"
        elif op == "clear":
            summary = "Cleared TODO list"
        else:
            summary = f"Operation: {op}"

        return ToolResult(
            data={"operation": op, "items": items, "count": result["count"]},
            summary=summary,
            raw=str(items),
            metadata={"tool": "todo_write", "type": "list"},
        )
