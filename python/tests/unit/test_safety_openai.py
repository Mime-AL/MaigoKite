"""OpenAI structured-output safety review: builder, parsing, degradation, fallback."""
from __future__ import annotations

import json

import httpx
import pytest
from agent.safety.config import SAFETY_FORMATS, normalize_safety_settings
from agent.safety.formats.openai import SCHEMA_INSTRUCTION, degrade_to_json_object
from agent.safety.request_builders import (
    SafetyFormatError,
    SafetyReviewInput,
    build_review_request,
)
from agent.safety.reviewer import SafetyReviewer, SafetyReviewError

BASE_URL = "http://127.0.0.1:1234/v1"


def review_input() -> SafetyReviewInput:
    return SafetyReviewInput(model_id="m1", task_id="t1", step=2, delta="do the thing")


def openai_payload(**overrides: object) -> dict:
    payload = build_review_request("openai", state="", decision_model="qwen3", review=review_input())
    payload.update(overrides)
    return payload


def completion(content: object) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def make_reviewer(handler) -> SafetyReviewer:
    return SafetyReviewer(transport=httpx.MockTransport(handler))


class TestBuilder:
    def test_openai_is_a_supported_format(self):
        assert "openai" in SAFETY_FORMATS
        assert normalize_safety_settings({"request_format": "openai"})["request_format"] == "openai"

    def test_dispatch_builds_chat_completions_payload(self):
        payload = build_review_request(
            "openai", state="custom state", decision_model="qwen3", review=review_input(),
        )
        assert payload["model"] == "qwen3"
        assert payload["max_tokens"] == 5120
        assert [message["role"] for message in payload["messages"]] == ["system", "user"]
        assert payload["messages"][0]["content"].startswith("custom state")
        assert "do the thing" in payload["messages"][1]["content"]
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["response_format"]["json_schema"]["schema"]["required"] == ["risk_probability", "reason"]

    def test_empty_state_falls_back_to_openai_default(self):
        payload = openai_payload()
        assert SCHEMA_INSTRUCTION in payload["messages"][0]["content"]
        assert "risk" in payload["messages"][0]["content"].lower()

    def test_degrade_swaps_to_json_object_and_keeps_contract(self):
        degraded = degrade_to_json_object(openai_payload())
        assert degraded["response_format"] == {"type": "json_object"}
        # Schema text must stay in the prompt because json_object has no schema field.
        assert SCHEMA_INSTRUCTION in degraded["messages"][0]["content"]

    def test_unknown_format_still_rejected(self):
        with pytest.raises(SafetyFormatError):
            build_review_request("nope", state="", decision_model="m", review=review_input())


class TestResponseParsing:
    async def test_json_schema_success_blocks_over_threshold(self):
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["payload"] = json.loads(request.content)
            return httpx.Response(200, json=completion('{"risk_probability": 0.8, "reason": "secret exfil"}'))

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="k", request_format="openai", state="",
            decision_model="qwen3", review=review_input(), threshold=75,
        )
        assert seen["url"] == f"{BASE_URL}/chat/completions"
        assert seen["payload"]["response_format"]["type"] == "json_schema"
        assert result.risk_score == 80
        assert result.blocked is True
        assert result.reason == "risk_threshold_exceeded"

    async def test_score_equal_to_threshold_passes(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=completion('{"risk_probability": 0.75, "reason": "benign"}'))

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="", request_format="openai", state="",
            decision_model="qwen3", review=review_input(), threshold=75,
        )
        assert result.blocked is False
        assert result.reason == "reviewed"

    async def test_fenced_json_object_content_accepted(self):
        fenced = '```json\n{"risk_probability": 0.1, "reason": "ok"}\n```'

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=completion(fenced))

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="", request_format="openai", state="",
            decision_model="qwen3", review=review_input(), threshold=75,
        )
        assert result.risk_score == 10
        assert result.blocked is False

    async def test_content_part_list_accepted(self):
        parts = [{"type": "text", "text": '{"risk_probability": 0.4, "reason": "borderline"}'}]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=completion(parts))

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="", request_format="openai", state="",
            decision_model="qwen3", review=review_input(), threshold=75,
        )
        assert result.risk_score == 40

    @pytest.mark.parametrize("content", [
        "not json at all",
        '{"risk_probability": 1.5, "reason": "out of range"}',
        '{"risk_probability": -0.1, "reason": "negative"}',
        '{"risk_probability": true, "reason": "bool"}',
        '{"reason": "missing probability"}',
        '{"risk_probability": 0.5}',
        '{"risk_probability": 0.5, "reason": "   "}',
        '{"risk_probability": "0.5", "reason": "string probability"}',
        "",
    ])
    async def test_invalid_structured_output_raises_for_conservative_block(self, content):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=completion(content))

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="", request_format="openai", state="",
                decision_model="qwen3", review=review_input(), threshold=75,
            )

    async def test_missing_choices_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"foo": "bar"})

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="", request_format="openai", state="",
                decision_model="qwen3", review=review_input(), threshold=75,
            )


class TestDegradation:
    async def test_unsupported_json_schema_degrades_to_json_object(self):
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            payloads.append(payload)
            if payload.get("response_format", {}).get("type") == "json_schema":
                return httpx.Response(400, json={"error": {"message": "response_format unsupported"}})
            return httpx.Response(200, json=completion('{"risk_probability": 0.2, "reason": "low risk"}'))

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="", request_format="openai", state="",
            decision_model="qwen3", review=review_input(), threshold=75,
        )
        assert len(payloads) == 2
        assert payloads[0]["response_format"]["type"] == "json_schema"
        assert payloads[1]["response_format"] == {"type": "json_object"}
        assert SCHEMA_INSTRUCTION in payloads[1]["messages"][0]["content"]
        assert result.risk_score == 20
        assert result.blocked is False

    async def test_no_degrade_on_auth_error(self):
        calls: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(json.loads(request.content))
            return httpx.Response(401, json={"error": {"message": "bad key"}})

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="k", request_format="openai", state="",
                decision_model="qwen3", review=review_input(), threshold=75,
            )
        assert len(calls) == 1

    async def test_degrade_still_failing_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(422, json={"error": {"message": "invalid"}})

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="", request_format="openai", state="",
                decision_model="qwen3", review=review_input(), threshold=75,
            )


class TestLegacyFormatsUnchanged:
    async def test_jev_like_probability_path_still_works(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/systemone")
            return httpx.Response(200, json={
                "legend": {"0": "safe", "1": "dangerous"},
                "probabilities": {"0": 0.2, "1": 0.8},
            })

        result = await make_reviewer(handler).review(
            base_url=BASE_URL, api_key="", request_format="jev_like", state="",
            decision_model="kev", review=review_input(), threshold=75,
        )
        assert result.risk_score == 80
        assert result.blocked is True

    async def test_jev_like_missing_probability_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"legend": {"0": "safe"}, "probabilities": {}})

        with pytest.raises(SafetyReviewError):
            await make_reviewer(handler).review(
                base_url=BASE_URL, api_key="", request_format="jev_like", state="",
                decision_model="kev", review=review_input(), threshold=75,
            )
