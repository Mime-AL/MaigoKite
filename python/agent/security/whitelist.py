"""Whitelist - Manages allowed tools, commands, and resources."""

from __future__ import annotations

import fnmatch
import shlex
from pathlib import Path


class Whitelist:
    """Manages allowlists for tools, commands, and resources."""

    def __init__(self, tools: set[str] | None = None, command_prefixes: set[str] | None = None,
                 allowed_paths: set[str] | None = None) -> None:
        self._tools = set(tools or ())
        self._command_prefixes = set(command_prefixes or ())
        self._allowed_paths = set(allowed_paths or ())

    def add_tool(self, tool_name: str) -> None:
        self._tools.add(tool_name)

    def remove_tool(self, tool_name: str) -> None:
        self._tools.discard(tool_name)

    def is_tool_allowed(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def add_command_prefix(self, prefix: str) -> None:
        self._command_prefixes.add(prefix.strip())

    def is_command_allowed(self, command: str) -> bool:
        try:
            parts = shlex.split(command)
        except ValueError:
            return False
        normalized = " ".join(parts)
        return any(normalized == prefix or normalized.startswith(prefix + " ") for prefix in self._command_prefixes)

    def add_allowed_path(self, path_pattern: str) -> None:
        self._allowed_paths.add(str(Path(path_pattern).expanduser().resolve()))

    def is_path_allowed(self, path: str) -> bool:
        resolved = str(Path(path).expanduser().resolve())
        return any(fnmatch.fnmatch(resolved, pattern) or resolved == pattern or resolved.startswith(pattern.rstrip("/") + "/") for pattern in self._allowed_paths)
