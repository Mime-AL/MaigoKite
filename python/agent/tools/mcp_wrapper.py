"""MCPToolWrapper - Bridge between MCP tools and the agent tool interface."""

from __future__ import annotations

from typing import Any

from agent.tools.base import BaseTool, ExecutionContext, ToolResult, ToolResultStream


class MCPToolWrapper(BaseTool):
    """Wraps an MCP (Model Context Protocol) tool as a BaseTool."""

    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    @property
    def parameters_schema(self) -> dict[str, Any]:
        ...

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult | ToolResultStream:
        ...
