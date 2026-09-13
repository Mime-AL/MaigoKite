"""Conversation memory backed by LangChain's ``ConversationTokenBufferMemory``.

Wraps the internal state management of message history, summarisation, and
clearing behind the existing ``IConversationMemory`` contract.  Internally a
``ConversationTokenBufferMemory`` instance is used to track turn count, store
messages as LangChain ``BaseMessage`` objects, and evict older turns when the
token limit is reached.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain.chains import ConversationBufferMemory
from langchain_community.memory.token_buffer import ConversationTokenBufferMemory

from agent.memory.conversation import ConversationTurn, IConversationMemory


class ConversationMemory(IConversationMemory):
    """Persistent conversation history managed by ``ConversationTokenBufferMemory``.

    Args:
        llm: A callable that accepts ``(prompt: str, **kwargs) -> str``.
             Required for token-buffer eviction behaviour.
        max_token_limit: The maximum number of tokens retained in the buffer.
                         Older messages are dropped first when this is exceeded.
        input_key: Key used when extracting input from LLM chain calls.
        output_key: Key used when extracting output from LLM chain calls.
    """

    def __init__(
        self,
        llm: Any | None = None,
        max_token_limit: int = 2000,
        input_key: str = "input",
        output_key: str = "output",
    ) -> None:
        self._lock = asyncio.Lock()
        self._max_token_limit = max_token_limit

        # Buffer-based memory handles token-aware truncation internally.
        # If an LLM isn't provided we fall back to ConversationBufferMemory
        # which has no truncation but still manages a clean message list.
        if llm is not None:
            self._langmem: ConversationTokenBufferMemory = ConversationTokenBufferMemory(
                llm=llm,
                max_token_limit=max_token_limit,
                input_key=input_key,
                output_key=output_key,
                return_messages=True,
            )
        else:
            self._langmem = ConversationBufferMemory(
                input_key=input_key,
                output_key=output_key,
                return_messages=True,
            )
        self._turn_counter: int = 0

    @property
    def turn_count(self) -> int:
        """Number of conversation turns stored."""
        return self._turn_counter

    async def append(self, turn: ConversationTurn) -> None:
        """Append a single conversation turn.

        The turn data is pushed through the LangChain memory backend so
        token-buffer eviction can occur automatically if configured.

        Args:
            turn: The conversation turn to add.
        """
        async with self._lock:
            self._langmem.chat_memory.add_user_message(turn.content)
            if turn.role.lower() in ("ai", "assistant", "model"):
                self._langmem.chat_memory.add_ai_message(turn.content)
            else:
                self._langmem.chat_memory.add_user_message(turn.content)
            self._turn_counter += 1

    async def query(self, n: int | None = None) -> list[ConversationTurn]:
        """Retrieve the most recent *n* turns (or all if *n* is ``None``).

        Args:
            n: Maximum number of turns to return.

        Returns:
            A list of ``ConversationTurn`` objects ordered chronologically.
        """
        async with self._lock:
            messages = self._langmem.chat_memory.messages
            if n is not None:
                messages = messages[-n:]

            turns: list[ConversationTurn] = []
            for msg in messages:
                role = "user" if msg.type == "human" else "ai"
                turns.append(ConversationTurn(role=role, content=msg.content))
            return turns

    async def summarize(self, target_tokens: int) -> str:
        """Return a compact summary of the stored conversation.

        For ``ConversationTokenBufferMemory`` the truncation logic is already
        handled internally; this method returns the current (possibly truncated)
        buffer text as a single summary string.

        Args:
            target_tokens: Target token budget (honoured implicitly by the
                           underlying buffer when constructed with an LLM).

        Returns:
            A single string summarising the buffered conversation history.
        """
        async with self._lock:
            return self._langmem.buffer or ""

    async def clear(self) -> None:
        """Clear all stored conversation history."""
        async with self._lock:
            self._langmem.chat_memory.clear()
            self._turn_counter = 0
