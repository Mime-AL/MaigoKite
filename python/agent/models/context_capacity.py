"""Read serving capacity, not a model-name table or a second provider protocol."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from anthropic import BadRequestError as AnthropicBadRequestError
from openai import APIError
from pydantic import SecretStr

from agent.models.compatible_reasoning import ReasoningChatOpenAI
from agent.models.native_model import _is_local_endpoint


@dataclass(frozen=True, slots=True)
class ContextCapacity:
    tokens: int | None = None
    source: str | None = None
    status: str = "unknown"
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _positive_int(value: Any) -> int | None:
    return value if type(value) is int and 0 < value <= 9007199254740991 else None


def profile_capacity(model: Any) -> ContextCapacity:
    metadata = getattr(model, "metadata", None) or {}
    tokens = _positive_int(metadata.get("maigokite_context_window"))
    if tokens:
        return ContextCapacity(tokens, "model_profile", "known")
    # A compatible endpoint can serve a locally loaded model under a cloud
    # model's name. Its SDK lookup is NOT evidence of that server's capacity.
    if isinstance(model, ReasoningChatOpenAI):
        return ContextCapacity()
    tokens = _positive_int((getattr(model, "profile", None) or {}).get("max_input_tokens"))
    return ContextCapacity(tokens, "model_profile" if tokens else None, "known" if tokens else "unknown")


def _loaded_capacity(payload: Any, model_name: str) -> ContextCapacity:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        return ContextCapacity(status="unsupported_metadata")
    exact: list[Any] = []
    by_model: list[Any] = []
    matched = False
    for model in payload["models"]:
        if not isinstance(model, dict) or model.get("type") != "llm":
            continue
        matches_model = model.get("key") == model_name
        matched |= matches_model
        instances = model.get("loaded_instances")
        if not isinstance(instances, list):
            continue
        for instance in instances:
            if not isinstance(instance, dict):
                continue
            config = instance.get("config")
            capacity = config.get("context_length") if isinstance(config, dict) else None
            if instance.get("id") == model_name:
                exact.append(capacity)
                matched = True
            if matches_model:
                by_model.append(capacity)
    # No fuzzy/display-name matching and no max_context_length fallback.
    # Multiple instances may have different load settings; never guess a route.
    candidates = exact or by_model
    if len(candidates) != 1:
        status = "ambiguous_instance" if candidates else "not_loaded" if matched else "model_not_found"
        return ContextCapacity(status=status)
    tokens = _positive_int(candidates[0])
    return ContextCapacity(tokens, "lmstudio.loaded_instance" if tokens else None,
                           "known" if tokens else "unsupported_metadata")


def _catalog_capacity(payload: Any, model_name: str) -> ContextCapacity:
    """Only metadata for the exact configured model ID is evidence of capacity."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return ContextCapacity(status="unsupported_metadata")
    matches = [item for item in payload["data"] if isinstance(item, dict) and item.get("id") == model_name]
    if len(matches) != 1:
        return ContextCapacity(status="model_not_found" if not matches else "unsupported_metadata")
    for name in ("context_window", "context_length", "contextWindow", "max_model_len"):
        tokens = _positive_int(matches[0].get(name))
        if tokens:
            return ContextCapacity(tokens, "provider_metadata", "known")
    return ContextCapacity(status="unsupported_metadata")


async def _provider_capacity(model: ReasoningChatOpenAI) -> ContextCapacity:
    # Reuse the official SDK's auth/base URL and Core-owned transport. A borrowed
    # client view disables retries; cancelling this lookup cannot close the owner.
    client = model.root_async_client
    if client is None:
        return ContextCapacity(status="metadata_unavailable")
    try:
        async with asyncio.timeout(3):
            lookup = client.with_options(timeout=3, max_retries=0).with_streaming_response.models.list()
            async with lookup as response:
                body = bytearray()
                async for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 2 * 1024 * 1024:
                        return ContextCapacity(status="unsupported_metadata")
                return _catalog_capacity(json.loads(body), model.model_name)
    except APIError as error:
        code = getattr(error, "status_code", None)
        status = ("unauthorized" if code in {401, 403}
                  else "unsupported_metadata" if code in {404, 405}
                  else "metadata_unavailable")
        return ContextCapacity(status=status)
    except (httpx.HTTPError, TimeoutError, ValueError):
        return ContextCapacity(status="metadata_unavailable")


async def _lmstudio_capacity(model: ReasoningChatOpenAI) -> ContextCapacity:
    """Read a local serving instance; never send this endpoint to every vendor.

    Reuse the public HTTP client owned by the Core's compatible model factory.
    Cancellation closes this response, never the shared client. A proxy URL's
    prefix and authority are retained; credentials never follow redirects.
    """
    client = model.http_async_client
    if not isinstance(client, httpx.AsyncClient):
        return ContextCapacity(status="metadata_unavailable")
    base = urlsplit(str(model.openai_api_base or ""))
    if base.scheme not in {"http", "https"} or not base.netloc or base.query or base.fragment:
        return ContextCapacity(status="unsupported_metadata")
    prefix = base.path.rstrip("/")
    if prefix.endswith("/v1"):
        prefix = prefix[:-3]
    endpoint = urlunsplit((base.scheme, base.netloc, prefix + "/api/v1/models", "", ""))
    credential = model.openai_api_key
    if credential is not None and not isinstance(credential, SecretStr):
        # Core supplies a workspace SecretStr. An injected SDK callable may have
        # different auth semantics; do not invoke it for an unrelated endpoint.
        return ContextCapacity(status="metadata_unavailable")
    key = credential.get_secret_value() if credential is not None else ""
    headers = {"Accept": "application/json"}
    if key and key != "local-no-key":
        headers["Authorization"] = f"Bearer {key}"
    try:
        async with asyncio.timeout(3):
            async with client.stream("GET", endpoint, headers=headers, timeout=3, follow_redirects=False) as response:
                if response.status_code != 200:
                    status = ("unauthorized" if response.status_code in {401, 403}
                              else "unsupported_metadata" if response.status_code in {404, 405}
                              else "metadata_unavailable")
                    return ContextCapacity(status=status)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 2 * 1024 * 1024:
                        return ContextCapacity(status="unsupported_metadata")
                return _loaded_capacity(json.loads(body), model.model_name)
    except (httpx.HTTPError, TimeoutError, ValueError):
        # Do not put URLs, credentials or an HTML error body into events/prompts.
        return ContextCapacity(status="metadata_unavailable")


async def resolve_context_capacity(model: Any, previous: ContextCapacity | None = None) -> ContextCapacity:
    """Loaded window first; exact-model catalog/profile capacity second.

    Unknown services never inherit an OpenAI model's limits from an alias, and
    neither output max_tokens nor the product budget is a capacity fallback.
    """
    fallback = profile_capacity(model)
    if not isinstance(model, ReasoningChatOpenAI):
        return fallback
    local = _is_local_endpoint(model.openai_api_base)
    # Unsupported/denied probes are cached only for this run/model. Loaded local
    # observations are refreshed each turn so a changed load setting is visible.
    if previous and not local and (previous.status in {"unsupported_metadata", "unauthorized"}
                                  or previous.tokens):
        return previous if previous.tokens or not fallback.tokens else replace(fallback, status=previous.status)
    loaded = None
    if local:
        loaded = await _lmstudio_capacity(model)
        if loaded.tokens:
            return loaded
    if fallback.tokens:
        return fallback
    catalog = await _provider_capacity(model)
    if catalog.tokens:
        return catalog
    # Keep a local instance's more useful failure reason (not loaded/ambiguous)
    # rather than replacing it with a generic catalog-without-capacity response.
    if loaded is not None and loaded.status in {"not_loaded", "ambiguous_instance", "unauthorized"}:
        return loaded
    return catalog


def capacity_from_error(error: BaseException) -> tuple[ContextCapacity, int] | None:
    """Read an explicit server rejection receipt; never infer capacity from prose."""
    body = getattr(error, "body", None)
    for _ in range(4):
        if isinstance(body, str):
            # LM Studio may nest the engine's JSON in its outer error message.
            if len(body) > 65536 or "exceed_context_size_error" not in body or "{" not in body:
                return None
            try:
                body, _end = json.JSONDecoder().raw_decode(body[body.index("{"):])
            except ValueError:
                return None
        if not isinstance(body, dict):
            return None
        tokens = _positive_int(body.get("n_ctx"))
        used = _positive_int(body.get("n_prompt_tokens"))
        if body.get("type") == "exceed_context_size_error" and tokens and used:
            return ContextCapacity(tokens, "provider_error", "known"), used
        body = body.get("error", body.get("message"))
    return None


def is_context_overflow(error: BaseException) -> bool:
    """Only explicit provider rejection codes qualify, never an arbitrary 4xx/500."""
    if capacity_from_error(error) is not None:
        return True
    codes = {"context_length_exceeded", "context_window_exceeded", "exceed_context_size_error"}
    code = getattr(error, "code", None)
    if isinstance(code, str) and code in codes:
        return True
    body = getattr(error, "body", None)
    for _ in range(3):
        if not isinstance(body, dict):
            return False
        if any(isinstance(body.get(key), str) and body[key] in codes for key in ("code", "type")):
            return True
        # Anthropic uses invalid_request_error for many unrelated problems.
        # Its documented overflow message qualifies only on that SDK's 400.
        if isinstance(error, AnthropicBadRequestError) and body.get("type") == "invalid_request_error":
            message = body.get("message")
            if isinstance(message, str) and message.startswith("prompt is too long:"):
                return True
        body = body.get("error")
    return False
