"""User-profile memory backed by LangChain ``ConversationSummaryMemory``.

Provides a lightweight preference store keyed on ``(category, key)`` pairs.
When fetching the user-memory context for long conversations,
``ConversationSummaryMemory`` is used to summarise the relevant chat history
so that only the most pertinent information is presented to the model.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain.chains import ConversationSummaryMemory

from agent.memory.user import IUserMemory


class UserMemory(IUserMemory):
    """Persistent user profile and preference storage.

    Args:
        llm: A LangChain-compatible LLM (callable) used internally by
             ``ConversationSummaryMemory`` to compress conversation snippets.
        prompt: Optional custom prompt string for summary generation.
    """

    def __init__(self, llm: Any | None = None, prompt: str | None = None) -> None:
        self._lock = asyncio.Lock()
        self._preferences: dict[str, dict[str, Any]] = {}  # category -> {key: value}
        self._llm = llm
        self._summary_prompt = prompt

    # -- public interface (preserved) --------------------------------------

    async def save_preference(self, category: str, key: str, value: Any) -> None:
        """Persist a single user preference.

        Args:
            category: Logical grouping for the preference (e.g. ``"style"``).
            key: Unique key within the category.
            value: Preference value of any type.
        """
        async with self._lock:
            if category not in self._preferences:
                self._preferences[category] = {}
            self._preferences[category][key] = value

    async def get_preference(self, category: str, key: str) -> Any | None:
        """Retrieve a single user preference.

        Args:
            category: Logical grouping.
            key: Preference key.

        Returns:
            The stored value, or ``None`` if not found.
        """
        async with self._lock:
            return self._preferences.get(category, {}).get(key)

    async def delete_preference(self, category: str, key: str) -> None:
        """Remove a single preference.

        Args:
            category: Logical grouping.
            key: Preference key to remove.
        """
        async with self._lock:
            cat_prefs = self._preferences.get(category)
            if cat_prefs:
                cat_prefs.pop(key, None)

    async def list_categories(self) -> list[str]:
        """Return all categories that have at least one preference.

        Returns:
            A list of category names.
        """
        async with self._lock:
            return [c for c, prefs in self._preferences.items() if prefs]

    async def list_preferences(self, category: str) -> dict[str, Any]:
        """Return all preferences within a category.

        Args:
            category: Category name.

        Returns:
            A dictionary mapping preference keys to their values.
        """
        async with self._lock:
            return dict(self._preferences.get(category, {}))

    # -- summarisation helper ----------------------------------------------

    async def get_user_memory_context(
        self, messages: list[Any], max_summary_tokens: int = 500
    ) -> str:
        """Produce a concise summary of conversation messages for user-memory context.

        Internally uses LangChain's ``ConversationSummaryMemory`` to summarise
        a batch of ``BaseMessage`` objects so that the resulting text fits
        within *max_summary_tokens*.

        Args:
            messages: A list of LangChain ``BaseMessage`` objects.
            max_summary_tokens: Approximate token budget for the summary.

        Returns:
            A human-readable summary string, or an empty string if the input
            is empty.
        """
        if not messages:
            return ""

        if self._llm is None:
            # Fallback: concatenate content without summarisation.
            return "\n".join(getattr(m, "content", str(m)) for m in messages)

        summary_memory = ConversationSummaryMemory(
            llm=self._llm,
            prompt=self._summary_prompt,
            input_key="input",
            output_key="output",
            return_messages=False,
        )

        return summary_memory.predict_new_summary(messages.copy(), "")
