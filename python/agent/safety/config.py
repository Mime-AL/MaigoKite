"""Workspace safety-review settings: defaults, normalization, validation.

API DTO validation owns user-facing bounds (threshold range, list length,
field lengths). Normalization here merges persisted values over defaults so a
legacy or corrupted row can never make reads fail or silently widen a limit.
"""
from __future__ import annotations

from typing import Any

SAFETY_SETTING_KEY = "safety.policy"
SAFETY_CREDENTIAL_REFERENCE = "safety.decision_model"
# jev_like covers the jev request class and its open-source implementation kev.
SAFETY_FORMATS = ("jev_like", "laya", "openai")
# jev_like wire layouts: "message" puts the delta in state.message (best on the
# 0.8B model); "inline" embeds it in the question instructions (best on the 4B).
SAFETY_JEV_LAYOUTS = ("inline", "message")
DEFAULT_JEV_LAYOUT = "message"
MAX_TRUSTED_MODEL_IDS = 32
MAX_STATE_LENGTH = 4000


def default_safety_settings() -> dict[str, Any]:
    return {
        "enabled": False,
        "request_format": "jev_like",
        "jev_layout": DEFAULT_JEV_LAYOUT,
        "state": "",
        "decision_base_url": "",
        "decision_model": "",
        "trusted_model_ids": [],
        "risk_threshold": 75,
    }


def normalize_safety_settings(stored: Any) -> dict[str, Any]:
    """Merge stored settings over defaults; drop unknown and invalid values."""
    value = default_safety_settings()
    if not isinstance(stored, dict):
        return value
    if isinstance(stored.get("enabled"), bool):
        value["enabled"] = stored["enabled"]
    if stored.get("request_format") in SAFETY_FORMATS:
        value["request_format"] = stored["request_format"]
    if stored.get("jev_layout") in SAFETY_JEV_LAYOUTS:
        value["jev_layout"] = stored["jev_layout"]
    for key in ("state", "decision_base_url", "decision_model"):
        item = stored.get(key)
        if isinstance(item, str):
            value[key] = item
    threshold = stored.get("risk_threshold")
    # bool is an int subclass; never accept it as a threshold.
    if isinstance(threshold, int) and not isinstance(threshold, bool) and 0 <= threshold <= 100:
        value["risk_threshold"] = threshold
    trusted = stored.get("trusted_model_ids")
    if isinstance(trusted, list):
        ids: list[str] = []
        for item in trusted:
            # Whitelist matching happens per step; duplicates and empties add nothing.
            if isinstance(item, str) and item and item not in ids:
                ids.append(item)
        value["trusted_model_ids"] = ids[:MAX_TRUSTED_MODEL_IDS]
    return value
