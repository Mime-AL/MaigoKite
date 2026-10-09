"""Project provider-reported usage without inventing cache hits or prices."""

from __future__ import annotations

from typing import Any


def message_usage(message: Any) -> dict[str, int]:
    """Prefer LangChain's normalized counters, including nested cache details.

    Stream chunks contain usage deltas; callers aggregate them once per model
    request. Missing counters remain absent, not a fabricated zero cache hit.
    """
    metadata = getattr(message, "response_metadata", {}) or {}
    raw = getattr(message, "usage_metadata", None) or metadata.get("token_usage") or {}
    if not isinstance(raw, dict):
        return {}
    usage = {
        str(key): int(value)
        for key, value in raw.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0
    }
    for details_key, field, target in (
        ("input_token_details", "cache_read", "cache_read_tokens"),
        ("input_token_details", "cache_creation", "cache_creation_tokens"),
        ("output_token_details", "reasoning", "reasoning_tokens"),
        ("prompt_tokens_details", "cached_tokens", "cache_read_tokens"),
    ):
        details = raw.get(details_key)
        value = details.get(field) if isinstance(details, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            usage[target] = int(value)
    return usage
