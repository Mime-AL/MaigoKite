"""IEmbeddingProvider - Abstract interface for embedding model providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IEmbeddingProvider(ABC):
    """Interface for embedding model providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        ...

    @abstractmethod
    async def embed_single(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the embedding vectors."""
        ...


class BGEProvider(IEmbeddingProvider):
    """Local BGE embedding provider (default)."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def embed_single(self, text: str) -> list[float]:
        ...

    @property
    def model_name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...


class OpenAIEmbeddingProvider(IEmbeddingProvider):
    """OpenAI embedding provider."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def embed_single(self, text: str) -> list[float]:
        ...

    @property
    def model_name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...


class GTEProvider(IEmbeddingProvider):
    """GTE embedding provider."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def embed_single(self, text: str) -> list[float]:
        ...

    @property
    def model_name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...
