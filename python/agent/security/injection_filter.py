"""InjectionFilter - Sanitizes inputs to prevent injection attacks."""

from __future__ import annotations

from typing import Any


class InjectionFilter:
    """Filters and sanitizes user inputs to prevent injection attacks."""

    def sanitize_input(self, input_text: str) -> str:
        """Sanitize a string input."""
        ...

    def sanitize_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Sanitize tool arguments."""
        ...

    def detect_shell_injection(self, input_text: str) -> bool:
        """Check if input contains potential shell injection patterns."""
        ...

    def detect_llm_injection(self, input_text: str) -> bool:
        """Check if input contains potential prompt injection patterns."""
        ...
