"""ToolValidator - Validates tool inputs against JSON Schema."""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """Raised when tool argument validation fails."""

    def __init__(self, message: str, errors: list[dict[str, Any]]) -> None:
        ...


class ToolValidator:
    """Validates tool arguments against their registered JSON Schema."""

    def validate(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Validate arguments against the tool's parameter schema."""
        ...

    def get_errors(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Return validation errors without raising."""
        ...

    def sanitize(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Sanitize and coerce argument types according to the schema."""
        ...
