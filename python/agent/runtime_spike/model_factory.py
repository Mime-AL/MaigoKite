"""Thin Product ModelProfile -> LangChain BaseChatModel adapter for the spike."""

from __future__ import annotations

import os

import httpx

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.models.chat_adapter import _is_local_endpoint, normalize_openai_compatible_base_url
from agent.models.runtime import ChatModelSettings


def build_chat_model(profile: ChatModelSettings, api_key: str = "") -> BaseChatModel:
    """Build the native LangChain provider selected by a product model profile.

    The spike intentionally does not add another provider protocol, response DTO,
    fallback layer, or stream parser around these integrations.
    """
    profile.validate()
    provider = profile.provider
    base_url = normalize_openai_compatible_base_url(provider, profile.base_url)

    if provider in {"openai", "openai_compatible"}:
        key = api_key
        if provider == "openai":
            key = key or os.getenv("OPENAI_API_KEY", "")
            if not key:
                raise RuntimeError("provider 'openai' requires an API key")
        else:
            key = key or "local-no-key"
        if provider == "openai_compatible" or _is_local_endpoint(base_url):
            return ChatOpenAI(
                model=profile.model,
                api_key=SecretStr(key),
                base_url=base_url or None,
                temperature=profile.temperature,
                max_completion_tokens=profile.max_tokens,
                timeout=profile.timeout_seconds,
                streaming=True,
                http_client=httpx.Client(timeout=profile.timeout_seconds, trust_env=False),
                http_async_client=httpx.AsyncClient(timeout=profile.timeout_seconds, trust_env=False),
                http_socket_options=(),
            )
        return ChatOpenAI(
            model=profile.model,
            api_key=SecretStr(key),
            base_url=base_url or None,
            temperature=profile.temperature,
            max_completion_tokens=profile.max_tokens,
            timeout=profile.timeout_seconds,
            streaming=True,
        )

    if provider == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("provider 'anthropic' requires an API key")
        return ChatAnthropic(
            model_name=profile.model,
            api_key=SecretStr(key),
            base_url=base_url or None,
            temperature=profile.temperature,
            max_tokens_to_sample=profile.max_tokens,
            timeout=profile.timeout_seconds,
            streaming=True,
            stop=None,
        )

    if provider == "ollama":
        return ChatOllama(
            model=profile.model,
            base_url=base_url or "http://127.0.0.1:11434",
            temperature=profile.temperature,
            num_predict=profile.max_tokens,
            client_kwargs={"timeout": profile.timeout_seconds, "trust_env": False},
            async_client_kwargs={"timeout": profile.timeout_seconds, "trust_env": False},
        )

    raise ValueError(f"unsupported chat provider: {provider}")
