"""HITL - Human-In-The-Loop coordination for agent workflows."""

from __future__ import annotations

from typing import Any


class HITLRequest:
    """A request for human approval or intervention."""

    request_id: str
    question: str
    options: list[str]
    metadata: dict[str, Any]

    def __init__(
        self,
        request_id: str,
        question: str,
        options: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...


class HITLCoordinator:
    """Manages human-in-the-loop checkpoints in the agent workflow."""

    def __init__(self) -> None:
        ...

    async def pause_for_approval(self, request: HITLRequest) -> str:
        """Pause execution and wait for human decision."""
        ...

    async def resume_after_decision(self, request_id: str, decision: str) -> None:
        """Resume the workflow after a human decision."""
        ...

    async def cancel_pending_requests(self) -> None:
        """Cancel all pending HITL requests."""
        ...
