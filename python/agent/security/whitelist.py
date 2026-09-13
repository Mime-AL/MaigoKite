"""Whitelist - Manages allowed tools, commands, and resources."""

from __future__ import annotations

from typing import Any


class Whitelist:
    """Manages allowlists for tools, commands, and resources."""

    def add_tool(self, tool_name: str) -> None:
        ...

    def remove_tool(self, tool_name: str) -> None:
        ...

    def is_tool_allowed(self, tool_name: str) -> bool:
        ...

    def add_command_prefix(self, prefix: str) -> None:
        ...

    def is_command_allowed(self, command: str) -> bool:
        ...

    def add_allowed_path(self, path_pattern: str) -> None:
        ...

    def is_path_allowed(self, path: str) -> bool:
        ...
