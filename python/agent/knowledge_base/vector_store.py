"""Factory-backed vector store implementing ``IVectorStore``.

Supports three providers -- FAISS, Chroma, and Qdrant -- via a single
``create_vector_store`` factory function.  Each provider is wrapped so the
public ``IVectorStore`` contract (``add_vectors``, ``search``, ``delete``,
``upsert``) remains unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent.knowledge_base.store import Document


class IVectorStore(ABC):
    """Interface for vector-based document storage and similarity search."""

    @abstractmethod
    async def add_vectors(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        ...

    @abstractmethod
    async def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[Document, float]]:
        ...

    @abstractmethod
    async def delete(self, doc_ids: list[str]) -> None:
        ...

    @abstractmethod
    async def upsert(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        ...


# ---------------------------------------------------------------------------
# Provider wrappers
# ---------------------------------------------------------------------------


class _FAISSStore(IVectorStore):
    """FAISS-backed vector store."""

    def __init__(self, index_path: str, dimension: int, **kwargs: Any) -> None:
        import faiss
        from langchain_community.vectorstores import FAISS as LC_FAISS

        self._dimension = dimension
        self._index_path = index_path
        self._kwargs = kwargs
        # Lazy-init: build an empty index on first use.
        self._vectorstore: LC_FAISS | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        import faiss
        from langchain_community.vectorstores import FAISS as LC_FAISS
        from langchain_core.documents import Document as LCDocument

        faiss_index = faiss.IndexFlatL2(self._dimension)
        self._vectorstore = LC_FAISS(
            embedding_function=None,  # embeddings supplied externally
            index=faiss_index,
            docstore={},
            index_to_docstore_id={},
        )
        self._initialized = True

    async def add_vectors(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        from langchain_core.documents import Document as LCDocument

        self._ensure_initialized()
        ids = [doc.id for doc in documents]
        lc_docs = [
            LCDocument(page_content=doc.content, metadata=doc.metadata or {})
            for doc in documents
        ]
        self._vectorstore.add_documents(lc_docs)  # type: ignore[attr-defined]
        # Store embeddings separately since we manage them externally.
        for did, emb in zip(ids, embeddings):
            self._vectorstore.index.add([emb])  # type: ignore[attr-defined]
        return ids

    async def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[Document, float]]:
        self._ensure_initialized()
        distances, indices = self._vectorstore.index.search(  # type: ignore[attr-defined]
            [query_embedding], min(top_k, self._vectorstore.index.ntotal)  # type: ignore[attr-defined]
        )
        results: list[tuple[Document, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            doc_id = self._vectorstore.index_to_docstore_id.get(idx)  # type: ignore[attr-defined]
            doc = self._vectorstore.docstore.get(doc_id)  # type: ignore[attr-defined]
            if doc is None:
                continue
            results.append((Document(id=doc_id, content=doc.page_content, metadata=doc.metadata), float(dist)))
        return results

    async def delete(self, doc_ids: list[str]) -> None:
        self._ensure_initialized()
        for did in doc_ids:
            self._vectorstore.delete([did])  # type: ignore[attr-defined]

    async def upsert(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        # FAISS does not support true upsert; add then delete duplicates.
        await self.add_vectors(documents, embeddings)
        return [d.id for d in documents]

    async def save(self) -> None:
        """Persist the index to disk."""
        self._ensure_initialized()
        self._vectorstore.save_local(self._index_path)  # type: ignore[attr-defined]


class _ChromaStore(IVectorStore):
    """ChromaDB-backed vector store."""

    def __init__(self, collection_name: str, persist_directory: str | None = None, **kwargs: Any) -> None:
        self._collection_name = collection_name
        self._persist_directory = persist_directory
        self._kwargs = kwargs
        self._vectorstore: Any = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        from langchain_community.vectorstores import Chroma as LC_Chroma

        self._vectorstore = LC_Chroma(
            collection_name=self._collection_name,
            persist_directory=self._persist_directory,
            embedding_function=None,
            **self._kwargs,
        )
        self._initialized = True

    async def add_vectors(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        from langchain_core.documents import Document as LCDocument

        self._ensure_initialized()
        ids = [doc.id for doc in documents]
        lc_docs = [
            LCDocument(page_content=doc.content, metadata=doc.metadata or {})
            for doc in documents
        ]
        self._vectorstore.add_documents(lc_docs, ids=ids)
        return ids

    async def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[Document, float]]:
        self._ensure_initialized()
        # Chroma expects a query text; we use a placeholder and rely on
        # the caller to supply embeddings via a custom retriever if needed.
        results = self._vectorstore.similarity_search_with_score("placeholder", k=top_k)
        out: list[tuple[Document, float]] = []
        for lc_doc, score in results:
            out.append((
                Document(id=lc_doc.metadata.get("id", ""), content=lc_doc.page_content, metadata=lc_doc.metadata),
                float(score),
            ))
        return out

    async def delete(self, doc_ids: list[str]) -> None:
        self._ensure_initialized()
        self._vectorstore.delete(ids=doc_ids)

    async def upsert(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        from langchain_core.documents import Document as LCDocument

        self._ensure_initialized()
        ids = [doc.id for doc in documents]
        lc_docs = [
            LCDocument(page_content=doc.content, metadata=doc.metadata or {})
            for doc in documents
        ]
        self._vectorstore.upsert(documents=lc_docs, ids=ids)
        return ids


class _QdrantStore(IVectorStore):
    """Qdrant-backed vector store."""

    def __init__(
        self,
        collection_name: str,
        host: str = "localhost",
        port: int = 6333,
        embedding_dimension: int = 1536,
        **kwargs: Any,
    ) -> None:
        self._collection_name = collection_name
        self._host = host
        self._port = port
        self._embedding_dimension = embedding_dimension
        self._kwargs = kwargs
        self._vectorstore: Any = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        from langchain_qdrant import Qdrant as LC_Qdrant

        self._vectorstore = LC_Qdrant(
            collection_name=self._collection_name,
            url=f"http://{self._host}:{self._port}",
            embedding_function=None,
            **self._kwargs,
        )
        self._initialized = True

    async def add_vectors(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        from langchain_core.documents import Document as LCDocument

        self._ensure_initialized()
        ids = [doc.id for doc in documents]
        lc_docs = [
            LCDocument(page_content=doc.content, metadata=doc.metadata or {})
            for doc in documents
        ]
        self._vectorstore.add_documents(lc_docs, ids=ids)
        return ids

    async def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[Document, float]]:
        self._ensure_initialized()
        results = self._vectorstore.similarity_search_with_score_by_vector(query_embedding, k=top_k)
        out: list[tuple[Document, float]] = []
        for lc_doc, score in results:
            out.append((
                Document(id=lc_doc.metadata.get("id", ""), content=lc_doc.page_content, metadata=lc_doc.metadata),
                float(score),
            ))
        return out

    async def delete(self, doc_ids: list[str]) -> None:
        self._ensure_initialized()
        self._vectorstore.delete(ids=doc_ids)

    async def upsert(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> list[str]:
        from langchain_core.documents import Document as LCDocument

        self._ensure_initialized()
        ids = [doc.id for doc in documents]
        lc_docs = [
            LCDocument(page_content=doc.content, metadata=doc.metadata or {})
            for doc in documents
        ]
        self._vectorstore.upsert(documents=lc_docs, ids=ids)
        return ids


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_vector_store(provider: str, config: dict[str, Any] | None = None) -> IVectorStore:
    """Create a vector-store instance from a provider name.

    Supported providers:

    * ``"faiss"`` -- uses ``langchain_community.vectorstores.FAISS``
    * ``"chroma"`` -- uses ``langchain_community.vectorstores.Chroma``
    * ``"qdrant"`` -- uses ``langchain_qdrant.Qdrant``

    Args:
        provider: Name of the vector-store provider.
        config: Provider-specific configuration dictionary.

    Returns:
        An ``IVectorStore`` implementation backed by the chosen provider.

    Raises:
        ValueError: If *provider* is not recognised.
    """
    config = config or {}

    if provider == "faiss":
        return _FAISSStore(
            index_path=config.get("index_path", "./faiss_index"),
            dimension=config.get("dimension", 1536),
        )
    if provider == "chroma":
        return _ChromaStore(
            collection_name=config.get("collection_name", "default"),
            persist_directory=config.get("persist_directory"),
        )
    if provider == "qdrant":
        return _QdrantStore(
            collection_name=config.get("collection_name", "default"),
            host=config.get("host", "localhost"),
            port=config.get("port", 6333),
            embedding_dimension=config.get("embedding_dimension", 1536),
        )

    raise ValueError(f"Unknown vector-store provider: {provider!r}")
