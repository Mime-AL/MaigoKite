"""Document storage backed by LangChain ``Document``.

Replaces the custom ``Document`` data class with ``langchain_core.documents.Document``
while keeping the ``IDocumentStore`` abstract contract intact.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.documents import Document as LCDocument


class IDocumentStore(ABC):
    """Interface for storing and retrieving documents."""

    @abstractmethod
    async def add(self, document: LCDocument) -> str:
        ...

    @abstractmethod
    async def add_many(self, documents: list[LCDocument]) -> list[str]:
        ...

    @abstractmethod
    async def get(self, doc_id: str) -> LCDocument | None:
        ...

    @abstractmethod
    async def delete(self, doc_id: str) -> None:
        ...

    @abstractmethod
    async def update(
        self, doc_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...


class InMemoryDocumentStore(IDocumentStore):
    """A simple in-memory implementation of ``IDocumentStore``.

    Documents are stored using ``langchain_core.documents.Document`` under the hood.
    Useful for prototyping or when an external vector-store backend is not needed.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._docs: dict[str, LCDocument] = {}

    async def add(self, document: LCDocument) -> str:
        """Add a single document.

        Args:
            document: A LangChain ``Document`` instance.

        Returns:
            The document's unique identifier (taken from ``metadata["id"]`` or generated).
        """
        async with self._lock:
            doc_id = document.metadata.get("id", "")
            if not doc_id:
                doc_id = str(len(self._docs))
                document.metadata = {**document.metadata, "id": doc_id}
            self._docs[doc_id] = document
            return doc_id

    async def add_many(self, documents: list[LCDocument]) -> list[str]:
        """Add multiple documents at once.

        Args:
            documents: List of LangChain ``Document`` instances.

        Returns:
            List of assigned document IDs.
        """
        async with self._lock:
            ids: list[str] = []
            for doc in documents:
                doc_id = doc.metadata.get("id", "")
                if not doc_id:
                    doc_id = str(len(self._docs))
                    updated_meta = {**doc.metadata, "id": doc_id}
                    doc = LCDocument(page_content=doc.page_content, metadata=updated_meta)
                self._docs[doc_id] = doc
                ids.append(doc_id)
            return ids

    async def get(self, doc_id: str) -> LCDocument | None:
        """Retrieve a single document by ID.

        Args:
            doc_id: The document identifier.

        Returns:
            The ``LCDocument`` if found, otherwise ``None``.
        """
        async with self._lock:
            return self._docs.get(doc_id)

    async def delete(self, doc_id: str) -> None:
        """Delete a document by ID.

        Args:
            doc_id: The document identifier to remove.
        """
        async with self._lock:
            self._docs.pop(doc_id, None)

    async def update(
        self, doc_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Update the content and optional metadata of an existing document.

        Args:
            doc_id: Identifier of the document to update.
            content: New page content.
            metadata: New metadata dictionary (merged with existing).
        """
        async with self._lock:
            doc = self._docs.get(doc_id)
            if doc is None:
                return
            new_metadata = {**(doc.metadata or {}), **(metadata or {})}
            self._docs[doc_id] = LCDocument(
                page_content=content,
                metadata=new_metadata,
            )

    async def count(self) -> int:
        """Return the total number of stored documents.

        Returns:
            Integer count of documents.
        """
        async with self._lock:
            return len(self._docs)
