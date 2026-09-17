"""Conversation-memory value types and token-bounded implementation."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str


class ConversationMemory:
    def __init__(self, max_token_limit: int = 2000, **_: object) -> None:
        self._max_tokens = max_token_limit
        self._turns: list[ConversationTurn] = []
        self._lock = asyncio.Lock()

    @staticmethod
    def _tokens(turn: ConversationTurn) -> int:
        return max(1, (len(turn.content) + 3) // 4)

    async def append(self, turn: ConversationTurn) -> None:
        async with self._lock:
            self._turns.append(turn)
            while len(self._turns) > 1 and sum(self._tokens(item) for item in self._turns) > self._max_tokens:
                self._turns.pop(0)

    async def query(self, n: int | None = None) -> list[ConversationTurn]:
        async with self._lock:
            turns = self._turns if n is None else self._turns[-n:]
            return list(turns)

    async def summarize(self, target_tokens: int) -> str:
        turns = await self.query()
        text = "\n".join(f"{turn.role}: {turn.content}" for turn in turns)
        return text[-max(1, target_tokens) * 4 :]

    async def clear(self) -> None:
        async with self._lock:
            self._turns.clear()

    @property
    def turn_count(self) -> int:
        return len(self._turns)
