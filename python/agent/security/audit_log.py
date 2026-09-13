"""AuditLog - Records security-relevant events for compliance and debugging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuditEntry:
    """A single audit log entry."""

    timestamp: datetime = field(default_factory=datetime.now)
    actor: str = ""
    action: str = ""
    resource: str = ""
    result: str = "success"
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None


class AuditLog:
    """Records and queries security-relevant audit events."""

    def record(self, entry: AuditEntry) -> None:
        ...

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditEntry]:
        ...

    def export(self, format: str = "json") -> str:
        ...
