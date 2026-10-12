"""Prompt safety review: workspace settings and decision-model request building.

Configuration is stored under the workspace setting key ``safety.policy``.
The decision-model API key lives in the credential store under
``safety.decision_model`` and never enters settings or events.

Phase A ships settings normalization only. The request builder library
(``request_builders`` and ``formats``) arrives with the runtime hook.
"""

from agent.safety.config import (
    SAFETY_CREDENTIAL_REFERENCE,
    SAFETY_FORMATS,
    SAFETY_SETTING_KEY,
    default_safety_settings,
    normalize_safety_settings,
)

__all__ = [
    "SAFETY_CREDENTIAL_REFERENCE",
    "SAFETY_FORMATS",
    "SAFETY_SETTING_KEY",
    "default_safety_settings",
    "normalize_safety_settings",
]
