"""ChatAdapter – LangChain-backed implementation of IChatProvider.

Wraps ``ChatOpenAI``, ``ChatAnthropic``, ``ChatOllama``, and similar
providers behind the stable ``IChatProvider`` contract so the rest of
the Agent Core never needs to import LangChain directly.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from agent.models.chat_provider import (
    ChatMessage,
    ChatResponse,
    IChatProvider,
)


class ChatAdapter(IChatProvider):
    """LangChain-based chat adapter that wraps multiple LLM providers.

    Supports ``openai``, ``anthropic``, and ``ollama`` out of the box.
    Automatically falls back to a secondary model when the primary call
    raises an exception.

    Args:
        provider: Provider identifier (``"openai"``, ``"anthropic"``, ``"ollama"``).
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
        self._extra = extra

        self._llm = self._build_llm(provider, model, extra)
        if fallback_provider and fallback_model:
            self._fallback_llm = self._build_llm(fallback_provider, fallback_model, extra)
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
        if env_key and not os.environ.get(env_key):
            raise RuntimeError(
                f"Provider '{provider}' requires the environment variable "
                f"'{env_key}' to be set."
            )

        if provider_lower == "openai":
            kwargs: dict[str, Any] = {
                "model": model,
                "temperature": extra.get("temperature", 0.7),
            }
            if extra.get("max_tokens"):
                kwargs["max_tokens"] = extra["max_tokens"]
            kwargs.update({k: v for k, v in extra.items() if k not in ("temperature", "max_tokens")})
            return ChatOpenAI(**kwargs)

        if provider_lower == "anthropic":
            kwargs = {
                "model": model,
                "temperature": extra.get("temperature", 0.7),
            }
            if extra.get("max_tokens"):
                kwargs["max_tokens"] = extra["max_tokens"]
            kwargs.update({k: v for k, v in extra.items() if k not in ("temperature", "max_tokens")})
            return ChatAnthropic(**kwargs)

        if provider_lower == "ollama":
            kwargs = {
                "model": model,
                "temperature": extra.get("temperature", 0.7),
            }
            if extra.get("max_tokens"):
                kwargs["max_tokens"] = extra["max_tokens"]
            kwargs.update({k: v for k, v in extra.items() if k not in ("temperature", "max_tokens")})
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
                result.append(AIMessage(content=content))
            elif role == "tool":
                result.append(ToolMessage(content=content, tool_call_id=msg.metadata.get("tool_call_id", "")))
            else:
                # Default to human for unknown roles.
                result.append(HumanMessage(content=content))
        return result

    @staticmethod
    def _from_langchain(response: Any) -> ChatResponse:
        """Wrap a LangChain ``AIMessage`` into our ``ChatResponse``."""
        usage: dict[str, int] = {}
        finish_reason: str | None = None

        if hasattr(response, "response_metadata"):
            meta = response.response_metadata or {}
            token_usage = meta.get("token_usage")
            if isinstance(token_usage, dict):
                usage = {k: int(v) for k, v in token_usage.items()}
            finish_reason = meta.get("finish_reason")

        return ChatResponse(
            content=response.content if isinstance(response.content, str) else "",
            role="assistant",
            usage=usage or None,
            finish_reason=finish_reason,
        )

    # ------------------------------------------------------------------
    # IChatProvider implementation
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
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

        effective_kwargs: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            effective_kwargs["max_tokens"] = max_tokens
        effective_kwargs.update(kwargs)

        # Try the primary model.
        try:
            resp = await self._llm.ainvoke(lc_msgs, config={"model_kwargs": effective_kwargs})
            return self._from_langchain(resp)
        except Exception:
            pass

        # Fall back to the secondary model if available.
        if self._fallback_llm:
            try:
                resp = await self._fallback_llm.ainvoke(lc_msgs)
                return self._from_langchain(resp)
            except Exception:
                pass

        # Neither worked – re-raise the original exception.
        raise

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Streaming chat with automatic fallback.

        Yields raw LangChain chunk objects.  Callers can convert them
        into ``ChatChunk`` or any other shape as needed.

        Raises:
            Exception: Re-raised when both primary and fallback providers fail.
        """
        lc_msgs = self._to_langchain(messages)

        effective_kwargs: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            effective_kwargs["max_tokens"] = max_tokens
        effective_kwargs.update(kwargs)

        # Try the primary model.
        try:
            async for chunk in self._llm.astream(lc_msgs, config={"model_kwargs": effective_kwargs}):
                yield chunk
            return
        except Exception:
            pass

        # Fall back.
        if self._fallback_llm:
            try:
                async for chunk in self._fallback_llm.astream(lc_msgs):
                    yield chunk
                return
            except Exception:
                pass

        raise

    @property
    def model_name(self) -> str:
        """Return the currently-selected model name."""
        return self.model
