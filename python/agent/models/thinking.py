"""Capability discovery and native SDK options, not a provider implementation.

Unknown endpoints never inherit a cloud model's capabilities from its name.
The UI consumes this same description that validates the execution setting.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx


@dataclass(frozen=True)
class ThinkingControl:
    kind: str = "unavailable"
    options: tuple[str, ...] = ()
    default: str = ""
    source: str = "unknown"
    reason: str = "unknown_capability"
    transport: str = ""

    def public(self) -> dict[str, Any]:
        return {"kind": self.kind, "options": list(self.options), "default": self.default,
                "source": self.source, "reason": self.reason}

    def model_options(self, value: str) -> dict[str, Any]:
        if not value:
            return {}  # Omit controls: preserve the serving default.
        if value not in self.options or self.kind == "unavailable":
            raise ValueError("此模型不支持所选思考设置，请刷新模型能力或恢复服务默认。")
        if self.transport == "ollama":
            return {"reasoning": {"on": True, "off": False}.get(value, value)}
        if self.transport == "anthropic":
            return {"thinking": {"type": "adaptive"}, "effort": value, "temperature": None}
        if self.transport == "responses":
            return {"use_responses_api": True, "reasoning": {"effort": value},
                    "store": False, "temperature": None}
        raise ValueError("当前接口尚未接入此思考控制，请恢复服务默认。")


def _control(values: Any, default: Any, source: str, transport: str) -> ThinkingControl:
    if not isinstance(values, (list, tuple)):
        return ThinkingControl(source=source)
    allowed = ("off", "on", "none", "minimal", "low", "medium", "high", "xhigh", "max")
    options = tuple(item for item in allowed if item in values)
    if not options:
        return ThinkingControl(source=source)
    kind = "toggle" if set(options) <= {"off", "on"} else "effort"
    if kind == "toggle" and default not in options:
        return ThinkingControl(source=source)
    return ThinkingControl(kind, options, default if default in options else "", source, "", transport)


def cloud_thinking(provider: str, model_name: str, model: Any) -> ThinkingControl:
    if provider == "openai":
        profile = getattr(model, "profile", None) or {}
        values = profile.get("reasoning_effort_levels")
        # Some installed models.dev snapshots overgeneralize the original GPT-5.
        # Keep the correction narrow; do not infer capabilities for unknown IDs.
        if re.fullmatch(r"gpt-5(?:-mini|-nano)?(?:-\d{4}-\d{2}-\d{2})?", model_name):
            values = ["minimal", "low", "medium", "high"]
        # The native SDK owns Responses conversion/tool calls. In particular,
        # newer reasoning models do not support tool calls on Chat Completions.
        return _control(values, profile.get("reasoning_effort_default"), "sdk_profile", "responses")
    if provider == "anthropic":
        # The installed Anthropic profile has no effort levels. These are exact
        # documented adaptive-thinking models, not a 'claude-*' name heuristic.
        # https://platform.claude.com/docs/en/build-with-claude/effort
        name = re.sub(r"-(?:\d{8}|latest)$", "", model_name)
        levels: dict[str, tuple[str, ...]] = {
            "claude-opus-4-6": ("low", "medium", "high", "max"),
            "claude-sonnet-4-6": ("low", "medium", "high", "max"),
        }
        for name_with_five_levels in (
            "claude-opus-4-7", "claude-opus-4-8", "claude-opus-5", "claude-opus-5-5",
            "claude-sonnet-5", "claude-sonnet-5-5", "claude-haiku-5-5",
            "claude-fable-5", "claude-fable-5-1", "claude-mythos-5", "claude-mythos-5-1",
        ):
            levels[name_with_five_levels] = ("low", "medium", "high", "xhigh", "max")
        default = "medium" if name in {"claude-opus-5-5", "claude-haiku-5-5"} else "high"
        return _control(levels.get(name), default, "provider_docs", "anthropic")
    return ThinkingControl()


async def serving_thinking(
    client: httpx.AsyncClient, provider: str, base_url: str, model_name: str, api_key: str,
) -> ThinkingControl:
    """Bounded metadata-only request; no generation, loading or guessed model ID."""
    base = urlsplit(base_url or ("http://localhost:11434" if provider == "ollama" else ""))
    if base.scheme not in {"http", "https"} or not base.netloc:
        return ThinkingControl()
    prefix = base.path.rstrip("/")
    if prefix.endswith("/v1"):
        prefix = prefix[:-3]
    endpoint = urlunsplit((base.scheme, base.netloc, prefix + (
        "/api/show" if provider == "ollama" else "/api/v1/models"
    ), "", ""))
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with asyncio.timeout(3):
            async with client.stream(
                "POST" if provider == "ollama" else "GET", endpoint,
                json={"model": model_name} if provider == "ollama" else None,
                headers=headers, timeout=3, follow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    return ThinkingControl(reason="metadata_unavailable")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 2 * 1024 * 1024:
                        return ThinkingControl(reason="metadata_unavailable")
                data = json.loads(body)
    except (httpx.HTTPError, TimeoutError, ValueError):
        return ThinkingControl(reason="metadata_unavailable")
    if not isinstance(data, dict):
        return ThinkingControl()
    if provider == "ollama":
        info = data.get("thinking")
        if not isinstance(info, dict):
            return ThinkingControl(source="ollama.show")
        def normalize(value: Any) -> Any:
            return "on" if value is True else "off" if value is False else value
        values = info.get("values")
        if not isinstance(values, list):
            return ThinkingControl(source="ollama.show")
        return _control([normalize(value) for value in values], normalize(info.get("default")),
                        "ollama.show", "ollama")
    entries = data.get("models")
    if not isinstance(entries, list):
        return ThinkingControl()
    matches = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") != "llm":
            continue
        instances = entry.get("loaded_instances")
        if not isinstance(instances, list):
            instances = []
        if entry.get("key") == model_name or any(
            isinstance(instance, dict) and instance.get("id") == model_name for instance in instances
        ):
            matches.append(entry)
    if len(matches) != 1:
        return ThinkingControl(source="lmstudio.models", reason="model_not_found")
    capabilities = matches[0].get("capabilities")
    info = capabilities.get("reasoning") if isinstance(capabilities, dict) else None
    if not isinstance(info, dict):
        return ThinkingControl(source="lmstudio.models")
    control = _control(info.get("allowed_options"), info.get("default"), "lmstudio.models", "responses")
    # LM Studio documents named effort via /v1/responses. Its native /api/v1/chat
    # on/off options are NOT evidence of the same switch on a compatible route.
    if any(option in {"off", "on"} for option in control.options):
        return ThinkingControl(source="lmstudio.models", reason="native_control_only")
    return control
