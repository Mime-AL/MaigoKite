"""PermissionManager - Controls tool access permissions."""

from __future__ import annotations

from typing import Any


class PermissionLevel:
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class PermissionManager:
    """Manages tool execution permissions and access control."""

    def grant(self, tool_name: str, permission: str) -> None:
        """Grant a permission for a tool."""
        ...

    def revoke(self, tool_name: str, permission: str) -> None:
        """Revoke a permission for a tool."""
        ...

    def check(self, tool_name: str, permission: str) -> bool:
        """Check if a permission is granted for a tool."""
        ...

    def set_scope(self, tool_name: str, scope: dict[str, Any]) -> None:
        """Set execution scope constraints for a tool."""
        ...

    def get_permissions(self, tool_name: str) -> set[str]:
        """Get all granted permissions for a tool."""
        ...
