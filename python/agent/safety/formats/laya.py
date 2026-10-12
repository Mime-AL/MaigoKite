"""LAYA safety review request format."""
from __future__ import annotations

from typing import Any

from agent.safety.formats.jev_like import DEFAULT_STATE
from agent.safety.request_builders import SafetyReviewInput


def build_request(*, state: str, decision_model: str, review: SafetyReviewInput) -> dict[str, Any]:
    return {
        "state": state.strip() or DEFAULT_STATE,
        "model": decision_model,
        "question": (
            f"Assess prompt risk from 0 to 100 for model {review.model_id} "
            f"at step {review.step}:\n{review.delta}"
        ),
        "context": {
            "task_id": review.task_id,
            "previous_model_id": review.previous_model_id,
            "context": review.context,
        },
    }
