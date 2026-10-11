"""Thin reasoning-field preservation for OpenAI-compatible Chat Completions.

LangChain still owns HTTP/SSE, retries, tool parsing, usage and cancellation.
The two conversion overrides follow its maintained DeepSeek integration's
extension points. Remove them when ChatOpenAI preserves these response fields.
No request parameters or model-side thinking settings are changed.
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from openai import BaseModel

from agent.models.reasoning import visible_reasoning


def _reasoning_content(fields: dict[str, Any]) -> str:
    # Some gateways supply the same text under several aliases. Pick one,
    # rather than duplicating it or displaying opaque reasoning_details JSON.
    for key in ("reasoning_content", "reasoning", "thinking", "reasoning_details"):
        if text := visible_reasoning(fields.get(key)):
            return text
    return ""


class ReasoningChatOpenAI(ChatOpenAI):
    """Keep exposed provider text separate from the upstream answer/tool stream."""

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict[str, Any],
        default_chunk_class: type[BaseMessage],
        base_generation_info: dict[str, Any] | None,
    ) -> ChatGenerationChunk | None:
        result = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info,
        )
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
        if result is not None and isinstance(result.message, AIMessageChunk) and choices:
            fields = choices[0].get("delta")
            if isinstance(fields, dict) and (text := _reasoning_content(fields)):
                result.message.additional_kwargs["reasoning_content"] = text
        return result

    def _create_chat_result(
        self,
        response: dict[str, Any] | BaseModel,
        generation_info: dict[str, Any] | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        if isinstance(response, dict):
            fields = [choice.get("message", {}) for choice in response.get("choices", [])]
        else:
            fields = [
                getattr(choice, "message").model_dump(exclude={"parsed"}, warnings=False)
                for choice in getattr(response, "choices", [])
            ]
        for generation, source in zip(result.generations, fields, strict=False):
            if isinstance(generation.message, AIMessage) and (text := _reasoning_content(source)):
                generation.message.additional_kwargs["reasoning_content"] = text
        return result
