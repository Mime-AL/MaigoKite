"""Error recovery strategies for agent execution."""

from __future__ import annotations

from typing import Any


class RecoveryStrategy:
    """Defines how to handle a failed execution step."""

    RETRY = "retry"
    FALLBACK = "fallback"
    ROLLBACK = "rollback"
    SKIP = "skip"


class ExecutionRecovery:
    """Handles failures with configurable recovery strategies."""

    def __init__(self, max_retries: int = 3) -> None:
        ...

    async def handle_failure(
        self,
        error: Exception,
        strategy: str = RecoveryStrategy.RETRY,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply the recovery strategy and return the outcome."""
        ...

    def register_fallback(
        self, tool_name: str, fallback_handler: Any
    ) -> None:
        """Register a fallback handler for a specific tool."""
        ...

    def register_retry_policy(
        self, tool_name: str, max_retries: int, backoff_factor: float
    ) -> None:
        """Configure retry policy for a specific tool."""
        ...
