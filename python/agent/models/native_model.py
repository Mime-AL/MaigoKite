"""Native LangChain model construction and Core-owned client cleanup.

No message protocol, fallback loop or tool-call parsing lives here. The legacy
ChatAdapter also delegates construction here until its callers are migrated.
"""
from __future__ import annotations

import inspect
import ipaddress
import os
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

import httpx
from langchain_core.language_models.chat_models import BaseChatModel

_KEY_ENV = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai_compatible": "", "ollama": ""}


def _is_local_endpoint(value: Any) -> bool:
    if not value:
        return False
    hostname = urlparse(str(value)).hostname or ""
    if hostname == "localhost" or hostname.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or address.is_private


def normalize_openai_compatible_base_url(provider: str, value: Any) -> str:
    """Repair the legacy LM Studio default URL without changing custom gateways."""
    base_url = str(value or "").strip().rstrip("/")
    if provider.lower() != "openai_compatible" or not base_url:
        return base_url
    parsed = urlparse(base_url)
    try:
        port = parsed.port
    except ValueError:
        return base_url
    if port == 1234 and parsed.path in {"", "/"}:
        return parsed._replace(path="/v1").geturl().rstrip("/")
    return base_url


def build_chat_model(provider: str, model: str, **extra: Any) -> BaseChatModel:
    provider_lower = provider.lower()

    # Validate API key for providers that need one.
    env_key = _KEY_ENV.get(provider_lower)
    explicit_key = str(extra.get("api_key") or "")
    if env_key and not (explicit_key or os.environ.get(env_key)):
        raise RuntimeError(
            f"Provider '{provider}' requires the environment variable "
            f"'{env_key}' to be set."
        )

    if provider_lower in {"openai", "openai_compatible"}:
        from langchain_openai import ChatOpenAI
        openai_key = explicit_key or "local-no-key"
        base_url = normalize_openai_compatible_base_url(
            provider_lower, extra.get("base_url")
        )
        if provider_lower == "openai":
            openai_key = explicit_key or os.environ.get("OPENAI_API_KEY") or ""
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": extra.get("temperature", 0.7),
            "api_key": openai_key,
        }
        if extra.get("max_tokens"):
            kwargs["max_completion_tokens"] = extra["max_tokens"]
        if base_url:
            kwargs["base_url"] = base_url
        if extra.get("timeout"):
            kwargs["timeout"] = extra["timeout"]
        if provider_lower == "openai_compatible" or _is_local_endpoint(base_url):
            timeout = extra.get("timeout") or 60
            kwargs["http_client"] = httpx.Client(timeout=timeout, trust_env=False)
            kwargs["http_async_client"] = httpx.AsyncClient(timeout=timeout, trust_env=False)
            kwargs["http_socket_options"] = ()
        kwargs.update({k: v for k, v in extra.items() if k not in ("temperature", "max_tokens", "api_key", "base_url", "timeout")})
        return ChatOpenAI(**kwargs)

    if provider_lower == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kwargs = {
            "model": model,
            "temperature": extra.get("temperature", 0.7),
            "api_key": explicit_key or os.environ.get("ANTHROPIC_API_KEY"),
        }
        if extra.get("max_tokens"):
            kwargs["max_tokens_to_sample"] = extra["max_tokens"]
        if extra.get("base_url"):
            kwargs["base_url"] = extra["base_url"]
        if extra.get("timeout"):
            kwargs["timeout"] = extra["timeout"]
        kwargs.update({k: v for k, v in extra.items() if k not in ("temperature", "max_tokens", "api_key", "base_url", "timeout")})
        return ChatAnthropic(**kwargs)

    if provider_lower == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise RuntimeError("Ollama support requires the langchain-ollama package") from exc
        kwargs = {
            "model": model,
            "temperature": extra.get("temperature", 0.7),
        }
        if extra.get("max_tokens"):
            kwargs["num_predict"] = extra["max_tokens"]
        if extra.get("base_url"):
            kwargs["base_url"] = extra["base_url"]
        if extra.get("timeout"):
            kwargs["client_kwargs"] = {"timeout": extra["timeout"], "trust_env": False}
            kwargs["async_client_kwargs"] = {"timeout": extra["timeout"], "trust_env": False}
        else:
            kwargs["client_kwargs"] = {"trust_env": False}
            kwargs["async_client_kwargs"] = {"trust_env": False}
        kwargs.update({k: v for k, v in extra.items() if k not in ("temperature", "max_tokens", "api_key", "base_url", "timeout")})
        return ChatOllama(**kwargs)

    raise ValueError(
        f"Unsupported chat provider '{provider}'. "
        f"Supported: {list(_KEY_ENV.keys())}"
    )


async def close_chat_models(models: Iterable[Any]) -> None:
    """Close only clients owned by these models; Core calls this after runs stop."""
    closed: set[int] = set()
    for llm in models:
        if llm is None:
            continue
        module = type(llm).__module__
        if module.startswith("langchain_openai"):
            attributes = ("root_async_client", "root_client")
        elif module.startswith("langchain_ollama"):
            attributes = ("_async_client", "_client")
        else:
            # ChatAnthropic 1.x caches its transports process-wide. Closing
            # the private client poisons later instances in the same Core
            # process, so its official cache owns that transport lifecycle.
            continue
        for attribute in attributes:
            client = getattr(llm, attribute, None)
            if client is None or id(client) in closed:
                continue
            closed.add(id(client))
            close = getattr(client, "aclose", None) or getattr(client, "close", None)
            if close is None:
                continue
            result = close()
            if inspect.isawaitable(result):
                await result
