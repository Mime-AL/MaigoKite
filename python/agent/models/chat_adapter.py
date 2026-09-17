"""ChatAdapter – LangChain-backed implementation of IChatProvider.

Wraps ``ChatOpenAI``, ``ChatAnthropic``, ``ChatOllama``, and similar
providers behind the stable ``IChatProvider`` contract so the rest of
the Agent Core never needs to import LangChain directly.
"""

from __future__ import annotations

import ipaddress
import os
from typing import Any, AsyncIterator, Optional
from urllib.parse import urlparse

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agent.models.chat_provider import (
    ChatMessage,
    ChatResponse,
    ChatStreamChunk,
    IChatProvider,
    ToolCall,
    ToolCallChunk,
)


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


class ChatAdapter(IChatProvider):
    """LangChain-based chat adapter that wraps multiple LLM providers.

    Supports ``openai``, ``anthropic``, ``openai_compatible``, and ``ollama`` out of the box.
    Automatically falls back to a secondary model when the primary call
    raises an exception.

    Args:
        provider: Provider identifier (``"openai"``, ``"anthropic"``, ``"openai_compatible"``, ``"ollama"``).
        model: Model name to use for the primary provider.
        temperature: Sampling temperature passed to the underlying model.
        max_tokens: Hard cap on generated tokens.
        fallback_provider: Optional second provider for automatic failover.
        fallback_model: Optional second model name for the fallback provider.
        **extra: Additional keyword arguments forwarded to the LangChain
            constructor for the selected provider.

    Example::

        adapter = ChatAdapter(provider="openai", model="gpt-4o-mini")
        response = await adapter.chat([ChatMessage(role="user", content="Hello")])
    """

    # Mapping from provider string to the environment variable that holds
    # the corresponding API key.  Used to surface a clear error when a
    # key is missing.
    _KEY_ENV: dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai_compatible": "",
        "ollama": "",  # Ollama is typically local; no key required.
    }

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        fallback_provider: Optional[str] = None,
        fallback_model: Optional[str] = None,
        **extra: Any,
    ) -> None:
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        build_extra = {**extra, "temperature": temperature, "max_tokens": max_tokens}
        self._extra = build_extra

        self._llm = self._build_llm(provider, model, build_extra)
        if fallback_provider and fallback_model:
            self._fallback_llm = self._build_llm(fallback_provider, fallback_model, build_extra)
        else:
            self._fallback_llm: Any | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def _build_llm(
        provider: str,
        model: str,
        extra: dict[str, Any],
    ) -> Any:
        """Create a LangChain ``ChatModel`` instance for *provider* / *model*.

        Raises:
            ValueError: When *provider* is not recognised.
            RuntimeError: When the required API key env-var is missing.
        """
        provider_lower = provider.lower()

        # Validate API key for providers that need one.
        env_key = ChatAdapter._KEY_ENV.get(provider_lower)
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
            f"Supported: {list(ChatAdapter._KEY_ENV.keys())}"
        )

    # ------------------------------------------------------------------
    # Message conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_langchain(messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert our ``ChatMessage`` list to LangChain ``BaseMessage`` list."""
        result: list[BaseMessage] = []
        for msg in messages:
            role = msg.role.lower() if msg.role else ""
            content = msg.content or ""

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "user":
                result.append(HumanMessage(content=content))
            elif role == "assistant":
                tool_calls = msg.metadata.get("tool_calls", [])
                result.append(AIMessage(content=content, tool_calls=tool_calls))
            elif role == "tool":
                result.append(ToolMessage(content=content, tool_call_id=msg.metadata.get("tool_call_id", "")))
            else:
                # Default to human for unknown roles.
                result.append(HumanMessage(content=content))
        return result

    @staticmethod
    def _message_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if not isinstance(value, list):
            return ""
        parts: list[str] = []
        for block in value:
            if isinstance(block, str):
                parts.append(block)
            elif (
                isinstance(block, dict)
                and block.get("type") not in {"reasoning", "thinking"}
                and isinstance(block.get("text"), str)
            ):
                parts.append(block["text"])
        return "".join(parts)

    @staticmethod
    def _reasoning_text(chunk: Any) -> str:
        """Read provider-exposed reasoning without folding it into answer text."""
        parts: list[str] = []
        additional = getattr(chunk, "additional_kwargs", {}) or {}
        for key in ("reasoning_content", "reasoning", "thinking"):
            value = additional.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
        content = getattr(chunk, "content", "")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") not in {"reasoning", "thinking"}:
                    continue
                value = block.get("text") or block.get("thinking")
                if isinstance(value, str):
                    parts.append(value)
        return "".join(parts)

    @staticmethod
    def _from_langchain(response: Any) -> ChatResponse:
        """Wrap a LangChain ``AIMessage`` into our ``ChatResponse``."""
        usage: dict[str, int] = {}
        finish_reason: str | None = None

        if hasattr(response, "response_metadata"):
            meta = response.response_metadata or {}
            token_usage = meta.get("token_usage")
            if isinstance(token_usage, dict):
                usage = {
                    k: int(v)
                    for k, v in token_usage.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                }
            finish_reason = meta.get("finish_reason")

        tool_calls: list[ToolCall] = []
        for item in getattr(response, "tool_calls", []) or []:
            arguments = item.get("args", {}) if isinstance(item, dict) else {}
            if not isinstance(arguments, dict):
                arguments = {}
            tool_calls.append(ToolCall(
                id=str(item.get("id", "")),
                name=str(item.get("name", "")),
                arguments=arguments,
            ))
        return ChatResponse(
            content=ChatAdapter._message_text(response.content),
            role="assistant",
            usage=usage or None,
            finish_reason=finish_reason,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _with_tools(llm: Any, tools: list[dict[str, Any]] | None) -> Any:
        if not tools:
            return llm
        bind_tools = getattr(llm, "bind_tools", None)
        if bind_tools is None:
            raise RuntimeError("the configured model does not support tool calling")
        return bind_tools(tools)

    # ------------------------------------------------------------------
    # IChatProvider implementation
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Non-streaming chat call with automatic fallback.

        Args:
            messages: Ordered list of chat messages.
            temperature: Override the default temperature for this call.
            max_tokens: Override the default max-tokens for this call.
            **kwargs: Extra parameters forwarded to the underlying model.

        Returns:
            A ``ChatResponse`` containing the model's reply.

        Raises:
            Exception: Re-raised when both primary and fallback providers fail.
        """
        lc_msgs = self._to_langchain(messages)
        tools = kwargs.pop("tools", None)

        effective_kwargs: dict[str, Any] = {
            "temperature": self.temperature if temperature is None else temperature,
        }
        effective_max_tokens = self.max_tokens if max_tokens is None else max_tokens
        if effective_max_tokens is not None:
            effective_kwargs["max_tokens"] = effective_max_tokens
        effective_kwargs.update(kwargs)

        # Try the primary model.
        primary_error: Exception | None = None
        try:
            resp = await self._with_tools(self._llm, tools).ainvoke(lc_msgs, **effective_kwargs)
            return self._from_langchain(resp)
        except Exception as exc:
            primary_error = exc

        # Fall back to the secondary model if available.
        if self._fallback_llm:
            try:
                resp = await self._with_tools(self._fallback_llm, tools).ainvoke(lc_msgs, **effective_kwargs)
                return self._from_langchain(resp)
            except Exception:
                pass

        # Neither worked – re-raise the original exception.
        assert primary_error is not None
        raise primary_error

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatStreamChunk]:
        """Streaming chat with automatic fallback.

        Yields provider-neutral text and tool-call deltas.

        Raises:
            Exception: Re-raised when both primary and fallback providers fail.
        """
        lc_msgs = self._to_langchain(messages)
        tools = kwargs.pop("tools", None)

        effective_kwargs: dict[str, Any] = {
            "temperature": self.temperature if temperature is None else temperature,
        }
        effective_max_tokens = self.max_tokens if max_tokens is None else max_tokens
        if effective_max_tokens is not None:
            effective_kwargs["max_tokens"] = effective_max_tokens
        effective_kwargs.update(kwargs)

        # Try the primary model.
        primary_error: Exception | None = None
        try:
            async for chunk in self._with_tools(self._llm, tools).astream(lc_msgs, **effective_kwargs):
                yield self._stream_chunk(chunk)
            return
        except Exception as exc:
            primary_error = exc

        # Fall back.
        if self._fallback_llm:
            try:
                async for chunk in self._with_tools(self._fallback_llm, tools).astream(lc_msgs, **effective_kwargs):
                    yield self._stream_chunk(chunk)
                return
            except Exception:
                pass

        assert primary_error is not None
        raise primary_error

    @staticmethod
    def _stream_chunk(chunk: Any) -> ChatStreamChunk:
        content = ChatAdapter._message_text(getattr(chunk, "content", ""))
        fragments: list[ToolCallChunk] = []
        raw_tool_chunks = getattr(chunk, "tool_call_chunks", []) or []
        if not raw_tool_chunks:
            raw_tool_chunks = getattr(chunk, "tool_calls", []) or []
        for position, item in enumerate(raw_tool_chunks):
            if not isinstance(item, dict):
                continue
            arguments = item.get("args", "")
            if isinstance(arguments, dict):
                import json
                arguments = json.dumps(arguments, ensure_ascii=False)
            index_value = item.get("index")
            fragments.append(ToolCallChunk(
                index=position if index_value is None else int(index_value),
                id=str(item.get("id", "") or ""),
                name=str(item.get("name", "") or ""),
                arguments=str(arguments or ""),
            ))
        metadata = getattr(chunk, "response_metadata", {}) or {}
        usage_metadata = getattr(chunk, "usage_metadata", {}) or {}
        usage = {
            str(key): int(value)
            for key, value in usage_metadata.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        return ChatStreamChunk(
            content=content,
            reasoning=ChatAdapter._reasoning_text(chunk),
            tool_call_chunks=fragments,
            finish_reason=metadata.get("finish_reason"),
            usage=usage,
        )

    @property
    def model_name(self) -> str:
        """Return the currently-selected model name."""
        return self.model

    async def aclose(self) -> None:
        """Release HTTP clients owned by the wrapped LangChain models."""
        for llm in (self._llm, self._fallback_llm):
            if llm is None:
                continue
            async_client = getattr(llm, "root_async_client", None)
            if async_client is not None and hasattr(async_client, "close"):
                await async_client.close()
            client = getattr(llm, "root_client", None)
            if client is not None and hasattr(client, "close"):
                client.close()
