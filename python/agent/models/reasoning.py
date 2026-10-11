"""Display only reasoning text actually exposed by a provider."""
from __future__ import annotations

from typing import Any


def visible_reasoning(value: Any) -> str:
    """Ignore signatures/encrypted payloads; never derive reasoning from an answer."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(visible_reasoning(item) for item in value)
    if isinstance(value, dict):
        if value.get("type") in {"reasoning.encrypted", "redacted_thinking"}:
            return ""
        for key in ("reasoning", "thinking", "text"):
            if isinstance(value.get(key), str):
                return str(value[key])
        return visible_reasoning(value.get("summary"))
    return ""
