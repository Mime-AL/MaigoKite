"""LAYA safety review: builder contract, model whitelist, endpoint, parsing."""
from __future__ import annotations

import json

import httpx
import pytest
from agent.safety.request_builders import (
    SafetyFormatError,
    SafetyReviewInput,
    build_review_request,
)
from agent.safety.reviewer import SafetyReviewer, SafetyReviewError

BASE_URL = "http://127.0.0.1:8000"


def review_input() -> SafetyReviewInput:
    return SafetyReviewInput(model_id="m1", task_id="t1", step=2, delta="do the thing")


def make_reviewer(handler) -> SafetyReviewer:
    return SafetyReviewer(transport=httpx.MockTransport(handler))


def laya_response(probabilities: dict | None = None) -> dict:
    answer: dict = {"type": "score"}
    if probabilities is not None:
        answer["legend"] = {"0": "safe", "1": "dangerous"}
        answer["probabilities"] = probabilities
    return {"answers": {"prompt_safety": answer}}


class TestBuilder:
    def test_contract_uses_questions_mapping(self):
        payload = build_review_request(
            "laya", state="", decision_model="", review=review_input(),
        )
        assert set(payload) == {"state", "model", "questions"}
        assert payload["state"] == {"message": "do the thing"}
        assert payload["model"] == "typed-decisions"
        question = payload["questions"]["prompt_safety"]
        assert question["type"] == "score"
        assert question["criteria"] == ["safe", "dangerous"]
        assert "guidance" not in question["instructions"]

    def test_guidance_attached_only_when_state_set(self):
        payload = build_review_request(
            "laya", state="  custom guidance  ", decision_model="english",
            review=review_input(),
        )
        assert payload["state"] == {"guidance": "custom guidance", "message": "do the thing"}
        assert payload["model"] == "english"
        instructions = payload["questions"]["prompt_safety"]["instructions"]
        assert instructions.startswith("Follow the classification guidance in `guidance`.")

    @pytest.mark.parametrize("decision_model", ["English", "TYPED-DECISIONS", " english "])
    def test_model_case_normalized_within_whitelist(self, decision_model):
        payload = build_review_request(
            "laya", state="", decision_model=decision_model, review=review_input(),
        )
        assert payload["model"] in {"english", "typed-decisions"}

    @pytest.mark.parametrize("decision_model", ["multilingual", "some-other-model", "laya"])
    def test_disallowed_model_rejected(self, decision_model):
        with pytest.raises(SafetyFormatError):
            build_review_request(
                "laya", state="", decision_model=decision_model, review=review_input(),
            )


class TestReviewer:
    async def test_appends_predict_suffix_and_parses_dangerous_probability(self):
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["payload"] = json.loads(request.content)
            return httpx.Response(200, json=laya_response({"0": 0.1, "1": 0.9}))

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="", request_format="laya", state="",
            decision_model="", review=review_input(), threshold=75,
        )
        assert seen["url"] == f"{BASE_URL}/predict"
        assert seen["payload"]["questions"]["prompt_safety"]["criteria"] == ["safe", "dangerous"]
        assert result.risk_score == 90
        assert result.blocked is True
        assert result.reason == "risk_threshold_exceeded"

    async def test_existing_predict_suffix_not_duplicated(self):
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            return httpx.Response(200, json=laya_response({"0": 0.95, "1": 0.05}))

        result = await make_reviewer(handler).review(
            base_url=f"{BASE_URL}/predict", api_key="", request_format="laya", state="",
            decision_model="english", review=review_input(), threshold=75,
        )
        assert seen["url"] == f"{BASE_URL}/predict"
        assert result.risk_score == 5
        assert result.blocked is False
        assert result.reason == "reviewed"

    async def test_score_equal_to_threshold_passes(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=laya_response({"0": 0.25, "1": 0.75}))

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="", request_format="laya", state="",
            decision_model="english", review=review_input(), threshold=75,
        )
        assert result.blocked is False

    async def test_missing_dangerous_probability_raises_for_conservative_block(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=laya_response(None))

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="", request_format="laya", state="",
                decision_model="english", review=review_input(), threshold=75,
            )

    async def test_http_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"detail": "prediction failed"})

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="", request_format="laya", state="",
                decision_model="english", review=review_input(), threshold=75,
            )

    async def test_disallowed_model_raises_for_conservative_block(self):
        def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
            raise AssertionError("no request should be sent")

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="", request_format="laya", state="",
                decision_model="multilingual", review=review_input(), threshold=75,
            )
