"""Compatibility entry for spike callers; production owns model construction."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from agent.models.native_model import build_chat_model as build_native_chat_model
from agent.models.runtime import ChatModelSettings


def build_chat_model(profile: ChatModelSettings, api_key: str = "") -> BaseChatModel:
    profile.validate()
    return build_native_chat_model(
        provider=profile.provider,
        model=profile.model,
        api_key=api_key,
        base_url=profile.base_url or ("http://127.0.0.1:11434" if profile.provider == "ollama" else None),
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
        timeout=profile.timeout_seconds,
        **({"streaming": True} if profile.provider != "ollama" else {}),
    )
