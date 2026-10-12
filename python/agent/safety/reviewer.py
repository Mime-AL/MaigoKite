"""Execute and normalize prompt safety review service calls."""
from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from agent.safety.formats.jev_like import DEFAULT_STATE
from agent.safety.request_builders import SafetyReviewInput, build_review_request

logger = logging.getLogger("maigokite.agent.safety")


@dataclass(frozen=True, slots=True)
class SafetyReviewResult:
    review_id: str
    model_id: str
    request_format: str
    risk_score: int | None
    threshold: int
    skipped: bool
    skip_reason: str | None
    blocked: bool
    reason: str


class SafetyReviewError(RuntimeError):
    """The safety service failed or returned an unusable response."""


def _find_danger_probability(value: Any) -> float | None:
    if isinstance(value, dict):
        probabilities = value.get("probabilities")
        legend = value.get("legend")
        if isinstance(probabilities, dict) and isinstance(legend, dict):
            dangerous_keys = {
                str(key) for key, label in legend.items()
                if isinstance(label, str) and label.strip().lower() == "dangerous"
            }
            for key in dangerous_keys:
                candidate = probabilities.get(key)
                if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                    return float(candidate)
        for item in value.values():
            found = _find_danger_probability(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_danger_probability(item)
            if found is not None:
                return found
    return None


class SafetyReviewer:
    def __init__(self, *, timeout: float = 12.0) -> None:
        self.timeout = timeout

    async def review(
        self,
        *,
        base_url: str,
        api_key: str,
        request_format: str,
        state: str,
        decision_model: str,
        review: SafetyReviewInput,
        threshold: int,
    ) -> SafetyReviewResult:
        review_id = "safety_" + uuid.uuid4().hex
        payload = build_review_request(
            request_format, state=state or DEFAULT_STATE,
            decision_model=decision_model, review=review,
        )
        endpoint = base_url.rstrip("/")
        if request_format == "jev_like":
            if endpoint.endswith("/v1"):
                endpoint += "/systemone"
            elif not endpoint.endswith("/v1/systemone"):
                endpoint += "/v1/systemone"
        headers = {"Authorization": "Bearer " + api_key} if api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SafetyReviewError("safety review service request failed") from exc
        dangerous_probability = _find_danger_probability(body)
        if dangerous_probability is None or not 0 <= dangerous_probability <= 1:
            raise SafetyReviewError(
                "safety review response did not contain a dangerous probability from 0 to 1"
            )
        score = dangerous_probability * 100
        reason = "risk_threshold_exceeded" if score > threshold else "reviewed"
        logger.info(
            "Safety decision: review_id=%s model_id=%s format=%s risk_score=%.2f "
            "threshold=%d blocked=%s reason=%s",
            review_id,
            review.model_id,
            request_format,
            score,
            threshold,
            score > threshold,
            reason,
        )
        return SafetyReviewResult(
            review_id=review_id, model_id=review.model_id, request_format=request_format,
            risk_score=round(score), threshold=threshold, skipped=False,
            skip_reason=None, blocked=score > threshold,
            reason=reason,
        )


def skipped_review(model_id: str, request_format: str, threshold: int) -> SafetyReviewResult:
    review_id = "safety_" + uuid.uuid4().hex
    logger.info(
        "Safety decision: review_id=%s model_id=%s format=%s risk_score=skipped "
        "threshold=%d blocked=False reason=trusted_model_skipped",
        review_id,
        model_id,
        request_format,
        threshold,
    )
    return SafetyReviewResult(
        review_id=review_id, model_id=model_id,
        request_format=request_format, risk_score=None, threshold=threshold,
        skipped=True, skip_reason="trusted_model", blocked=False, reason="trusted_model_skipped",
    )
