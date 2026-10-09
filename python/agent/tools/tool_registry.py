"""Single registry for native and MCP tools."""
from __future__ import annotations
from typing import Any
from collections.abc import Sequence
from agent.tools.base import BaseTool, ExecutionContext, ToolResult, ToolResultStream
from agent.tools.validator import ToolValidator

class ToolRegistry:
    DEFAULT_TOOLS = (
        "file_read", "file_write", "file_edit", "glob", "grep", "exec_command",
        "web_search", "web_fetch", "browser", "skill",
    )

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self.validator = ToolValidator(self.schema_for)

    def register(self, tool: BaseTool) -> None:
        if not tool.name or tool.name in self._tools:
            raise ValueError(f"tool already registered or invalid: {tool.name}")
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        self._tools.pop(tool_name, None)

    def get(self, tool_name: str) -> BaseTool | None:
        return self._tools.get(tool_name)

    def list_tools(self) -> list[BaseTool]:
        return [self._tools[name] for name in sorted(self._tools)]

    async def discover_mcp(
        self, client: Any, namespace: str, *,
        enabled_tools: list[str] | None = None, disabled_tools: Sequence[str] = (),
    ) -> list[BaseTool]:
        from agent.tools.mcp_wrapper import MCPToolWrapper
        discovered: list[BaseTool] = []
        for definition in await client.list_tools():
            source_name = str(definition.get("name", ""))
            if source_name in disabled_tools or (enabled_tools is not None and source_name not in enabled_tools):
                continue
            tool = MCPToolWrapper(client, definition, namespace)
            self.register(tool)
            discovered.append(tool)
        return discovered

    def schema_for(self, tool_name: str) -> dict[str, Any] | None:
        tool = self.get(tool_name)
        return None if tool is None else tool.parameters_schema

    async def invoke(self, tool_name: str, arguments: dict[str, Any], context: ExecutionContext) -> ToolResult | ToolResultStream:
        tool = self.get(tool_name)
        if tool is None:
            raise KeyError(f"unknown tool: {tool_name}")
        return await tool.execute(context, self.validator.sanitize(tool_name, arguments))
