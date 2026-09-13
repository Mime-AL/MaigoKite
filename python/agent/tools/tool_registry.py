"""ToolRegistry - Central registry for tool discovery and invocation."""

from __future__ import annotations

from typing import Any

from agent.tools.base import BaseTool


class ToolRegistry:
    """Manages registration, discovery, and invocation of tools."""

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        ...

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool by name."""
        ...

    def get(self, tool_name: str) -> BaseTool | None:
        """Retrieve a registered tool by name."""
        ...

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools."""
        ...

    def schema_for(self, tool_name: str) -> dict[str, Any] | None:
        """Get the JSON Schema for a specific tool's parameters."""
        ...

    async def invoke(self, tool_name: str, arguments: dict[str, Any], context: Any) -> Any:
        """Invoke a registered tool by name."""
        ...
