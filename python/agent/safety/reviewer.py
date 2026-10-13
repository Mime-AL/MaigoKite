"""Execute and normalize prompt safety review service calls."""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from agent.safety.config import DEFAULT_JEV_LAYOUT
from agent.safety.formats.openai import degrade_to_json_object
from agent.safety.request_builders import (
    SafetyFormatError,
    SafetyReviewInput,
    build_review_request,
)

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


# 4xx codes that mean "response_format unsupported" for OpenAI-compatible services.
_OPENAI_DEGRADE_STATUSES = frozenset({400, 404, 415, 422})


def _parse_openai_review(body: Any) -> tuple[float, str]:
    """Read normalized risk probability/reason from structured output."""
    content: Any = None
    if isinstance(body, dict):
        choices = body.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
    if isinstance(content, list):
        # Some compatible services return content parts instead of a plain string.
        content = "".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    if not isinstance(content, str) or not content.strip():
        raise SafetyReviewError("safety review response did not contain structured output")
    text = content.strip()
    if text.startswith("```"):
        # json_object mode lets some services wrap the JSON in a markdown fence.
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise SafetyReviewError("safety review structured output was not valid JSON") from exc
    if not isinstance(data, dict):
        raise SafetyReviewError("safety review structured output was not a JSON object")
    probability = data.get("risk_probability")
    if (
        isinstance(probability, bool)
        or not isinstance(probability, (int, float))
        or not 0 <= probability <= 1
    ):
        raise SafetyReviewError(
            "safety review structured output did not contain a risk_probability from 0 to 1"
        )
    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise SafetyReviewError("safety review structured output did not contain a reason")
    return float(probability), reason.strip()


class SafetyReviewer:
    def __init__(self, *, timeout: float = 12.0, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.timeout = timeout
        # Test seam: httpx.MockTransport exercises the full review path offline.
        self._transport = transport

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
        layout: str = DEFAULT_JEV_LAYOUT,
    ) -> SafetyReviewResult:
        review_id = "safety_" + uuid.uuid4().hex
        try:
            payload = build_review_request(
                request_format, state=state,
                decision_model=decision_model, review=review, layout=layout,
            )
        except SafetyFormatError as exc:
            raise SafetyReviewError("safety review request construction failed") from exc
        endpoint = base_url.rstrip("/")
        if request_format == "jev_like":
            if endpoint.endswith("/v1"):
                endpoint += "/systemone"
            elif not endpoint.endswith("/v1/systemone"):
                endpoint += "/v1/systemone"
        elif request_format == "laya" and not endpoint.endswith("/predict"):
            endpoint += "/predict"
        elif request_format == "openai" and not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        headers = {"Authorization": "Bearer " + api_key} if api_key else {}
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=False, transport=self._transport,
            ) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                if (
                    request_format == "openai"
                    and response.status_code in _OPENAI_DEGRADE_STATUSES
                    and payload.get("response_format", {}).get("type") == "json_schema"
                ):
                    # Structured-output mode rejected: retry once in json_object mode;
                    # the schema instruction already lives in the system message.
                    payload = degrade_to_json_object(payload)
                    response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SafetyReviewError("safety review service request failed") from exc
        model_reason = ""
        if request_format == "openai":
            probability, model_reason = _parse_openai_review(body)
            score = probability * 100
        else:
            dangerous_probability = _find_danger_probability(body)
            if dangerous_probability is None or not 0 <= dangerous_probability <= 1:
                raise SafetyReviewError(
                    "safety review response did not contain a dangerous probability from 0 to 1"
                )
            score = dangerous_probability * 100
        reason = "risk_threshold_exceeded" if score > threshold else "reviewed"
        logger.info(
            "Safety decision: review_id=%s model_id=%s format=%s risk_score=%.2f "
            "threshold=%d blocked=%s reason=%s model_reason=%s",
            review_id,
            review.model_id,
            request_format,
            score,
            threshold,
            score > threshold,
            reason,
            model_reason,
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
