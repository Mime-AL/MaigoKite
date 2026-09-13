"""Configuration management for the agent core."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """Manages agent configuration with reload support."""

    def __init__(self, config_path: Path | None = None) -> None:
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-separated key."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        ...

    def reload(self) -> None:
        """Reload configuration from disk."""
        ...

    @property
    def raw(self) -> dict[str, Any]:
        """Return the full configuration dictionary."""
        ...
