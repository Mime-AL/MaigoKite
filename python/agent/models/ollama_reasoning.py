"""Preserve default thinking text with the pinned langchain-ollama 1.1.0.

The native integration only preserves thinking when its reasoning flag is set.
Use that native conversion, but retain the original HTTP `think` parameter.
The conversion hooks depend on this integration's signatures. Remove them when
upstream retains returned thinking without requiring a request-side override.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_ollama import ChatOllama


class ReasoningChatOllama(ChatOllama):
    """Separate returned thinking from the answer while preserving the HTTP think value."""

    def _chat_params(
        self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        preserve_default = kwargs.pop("_maigokite_preserve_default_think", False)
        params = super()._chat_params(messages, stop, **kwargs)
        if preserve_default:
            params["think"] = None
        return params

    def _iterate_over_stream(
        self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        if kwargs.get("reasoning", self.reasoning) is None:
            kwargs = {**kwargs, "reasoning": True, "_maigokite_preserve_default_think": True}
        yield from super()._iterate_over_stream(messages, stop, **kwargs)

    async def _aiterate_over_stream(
        self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        if kwargs.get("reasoning", self.reasoning) is None:
            kwargs = {**kwargs, "reasoning": True, "_maigokite_preserve_default_think": True}
        async for chunk in super()._aiterate_over_stream(messages, stop, **kwargs):
            yield chunk
