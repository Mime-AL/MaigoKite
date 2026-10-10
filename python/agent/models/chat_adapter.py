"""ChatAdapter – LangChain-backed implementation of IChatProvider.

Wraps ``ChatOpenAI``, ``ChatAnthropic``, ``ChatOllama``, and similar
providers behind the stable ``IChatProvider`` contract so the rest of
the Agent Core never needs to import LangChain directly.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agent.models.native_model import (
    build_chat_model, close_chat_models,
    normalize_openai_compatible_base_url as normalize_openai_compatible_base_url,
)

from agent.models.chat_provider import (
    ChatMessage,
    ChatResponse,
    ChatStreamChunk,
    IChatProvider,
    ToolCall,
    ToolCallChunk,
)




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
        self._fallback_llm: Any | None
        if fallback_provider and fallback_model:
            self._fallback_llm = self._build_llm(fallback_provider, fallback_model, build_extra)
        else:
            self._fallback_llm = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def _build_llm(provider: str, model: str, extra: dict[str, Any]) -> Any:
        return build_chat_model(provider, model, **extra)

    # ------------------------------------------------------------------
    # Message conversion
    # ------------------------------------------------------------------

    @staticmethod
    def to_langchain_messages(messages: list[ChatMessage]) -> list[BaseMessage]:
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
        from agent.models.usage import message_usage

        usage = message_usage(response)
        finish_reason: str | None = None

        if hasattr(response, "response_metadata"):
            meta = response.response_metadata or {}
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
        lc_msgs = self.to_langchain_messages(messages)
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
        """Streaming chat with fallback only before the first emitted chunk.

        Yields provider-neutral text and tool-call deltas.

        Raises:
            Exception: Re-raised when both primary and fallback providers fail.
        """
        lc_msgs = self.to_langchain_messages(messages)
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
        emitted = False
        try:
            async for chunk in self._with_tools(self._llm, tools).astream(lc_msgs, **effective_kwargs):
                projected = self._stream_chunk(chunk)
                emitted = True
                yield projected
            return
        except Exception as exc:
            # Mixing two streams can concatenate unrelated tool IDs, names or
            # JSON argument fragments into a call neither provider requested.
            if emitted:
                raise
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
        from agent.models.usage import message_usage
        return ChatStreamChunk(
            content=content,
            reasoning=ChatAdapter._reasoning_text(chunk),
            tool_call_chunks=fragments,
            finish_reason=metadata.get("finish_reason"),
            usage=message_usage(chunk),
        )

    @property
    def model_name(self) -> str:
        """Return the currently-selected model name."""
        return self.model

    @property
    def langchain_model(self) -> Any:
        """Return the primary model for the production LangGraph runtime."""
        return self._llm

    async def aclose(self) -> None:
        await close_chat_models([self._llm, self._fallback_llm])
