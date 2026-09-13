"""Document retrieval backed by LangChain retrievers.

Implements the ``IRetriever`` contract with three retriever strategies:

* ``VectorStoreRetriever`` -- pure vector-store similarity search
* ``ContextualCompressionRetriever`` -- vector search followed by LLM-based
  contextual compression to prune irrelevant results
* ``EnsembleRetriever`` -- combines a semantic (vector) retriever with a
  keyword (BM25) retriever and merges their results via reciprocal-rank fusion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.documents import Document as LCDocument


class RetrievalResult:
    """A single result from a retrieval query."""

    document: LCDocument
    score: float

    def __init__(self, document: LCDocument, score: float) -> None:
        self.document = document
        self.score = score


class IRetriever(ABC):
    """Interface for querying and retrieving documents."""

    @abstractmethod
    async def retrieve(
        self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[RetrievalResult]:
        ...

    @abstractmethod
    async def retrieve_by_id(self, doc_id: str) -> LCDocument | None:
        ...


# ---------------------------------------------------------------------------
# Concrete retrievers
# ---------------------------------------------------------------------------


class VectorStoreRetriever(IRetriever):
    """Thin wrapper around LangChain's ``VectorStoreRetriever``.

    Args:
        vector_store: A LangChain-compatible vector store instance that
                      exposes a ``as_retriever()`` method or can be wrapped
                      in ``VectorStoreRetriever``.
        top_k: Default number of results to return.
    """

    def __init__(self, vector_store: Any, top_k: int = 5, **kwargs: Any) -> None:
        from langchain_community.vectorstores import VectorStoreRetriever

        self._vector_store = vector_store
        self._top_k = top_k
        if hasattr(vector_store, "as_retriever"):
            self._lc_retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": top_k, **kwargs},
            )
        else:
            # Fallback: the store itself may already be compatible.
            self._lc_retriever = VectorStoreRetriever(
                vectorstore=vector_store,
                search_type="similarity",
                search_kwargs={"k": top_k, **kwargs},
            )

    async def retrieve(
        self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[RetrievalResult]:
        """Retrieve documents for *query*.

        Args:
            query: Natural-language search string.
            top_k: Number of results to return.
            filters: Optional metadata filter dict passed through to the
                     underlying vector store.

        Returns:
            A list of ``RetrievalResult`` objects ordered by relevance.
        """
        kwargs: dict[str, Any] = {"k": top_k}
        if filters:
            kwargs["filter"] = filters
        lc_docs = self._lc_retriever.invoke(query)
        return [RetrievalResult(document=doc, score=0.0) for doc in lc_docs]

    async def retrieve_by_id(self, doc_id: str) -> LCDocument | None:
        """Fetch a single document by its ID.

        Uses the underlying store's ``get`` / ``fetch`` capability when available.

        Args:
            doc_id: Unique document identifier.

        Returns:
            The ``LCDocument`` if found, otherwise ``None``.
        """
        vc = getattr(self._vector_store, "vectorstore", self._vector_store)
        if hasattr(vc, "get"):
            result = vc.get(ids=[doc_id])
            if result and result.get("documents"):
                docs = []
                for i, doc_content in enumerate(result["documents"]):
                    meta = result.get("metadatas", [{}])[i] if result.get("metadatas") else {}
                    docs.append(LCDocument(page_content=doc_content, metadata=meta))
                return docs[0] if docs else None
        return None


class ContextualCompressionRetriever(IRetriever):
    """Combines a base vector store retriever with LLM-based contextual compression.

    Uses LangChain's ``ContextualCompressionRetriever`` paired with
    ``LLMChainFilter`` so that an LLM evaluates each retrieved document and
    drops those whose content is not relevant to the original query.

    Args:
        base_retriever: A LangChain retriever instance providing initial candidates.
        llm: A LangChain-compatible LLM used for contextual filtering.
        top_k: Default number of results before compression.
    """

    def __init__(self, base_retriever: Any, llm: Any, top_k: int = 20) -> None:
        from langchain.retrievers import ContextualCompressionRetriever
        from langchain.retrievers.document_compressors import LLMChainExtractor

        compressor = LLMChainExtractor.from_llm(llm)
        self._compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever,
        )
        self._top_k = top_k

    async def retrieve(
        self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[RetrievalResult]:
        """Retrieve and compress documents for *query*.

        Args:
            query: Natural-language search string.
            top_k: Number of final (post-compression) results.
            filters: Not supported with LLM compressor; ignored.

        Returns:
            A list of ``RetrievalResult`` objects.
        """
        lc_docs = self._compression_retriever.invoke(query)
        return [RetrievalResult(document=doc, score=0.0) for doc in lc_docs]

    async def retrieve_by_id(self, doc_id: str) -> LCDocument | None:
        base = getattr(self._compression_retriever, "base_retriever", None)
        if base is not None:
            retriever_cls = type(base).__name__
            if hasattr(base, "vectorstore"):
                vc = base.vectorstore
                if hasattr(vc, "get"):
                    result = vc.get(ids=[doc_id])
                    if result and result.get("documents"):
                        docs = []
                        for i, doc_content in enumerate(result["documents"]):
                            meta = result.get("metadatas", [{}])[i] if result.get("metadatas") else {}
                            docs.append(LCDocument(page_content=doc_content, metadata=meta))
                        return docs[0] if docs else None
        return None


class EnsembleRetriever(IRetriever):
    """Combines semantic and keyword search via reciprocal-rank fusion.

    Wraps LangChain's ``EnsembleRetriever`` which pairs a
    ``VectorStoreRetriever`` (semantic) with a ``BM25Retriever``
    (keyword) and merges scores using reciprocal rank fusion.

    Args:
        vector_store: A LangChain-compatible vector store.
        llm: Used to initialise the semantic embedding function when the
             vector store does not already have one.
        top_k: Default number of combined results to return.
    """

    def __init__(
        self,
        vector_store: Any,
        llm: Any | None = None,
        top_k: int = 5,
    ) -> None:
        from langchain.retrievers import EnsembleRetriever as LC_EnsembleRetriever
        from langchain_community.retrievers import BM25Retriever
        from langchain_community.vectorstores import VectorStoreRetriever

        semantic_retriever = VectorStoreRetriever(
            vectorstore=vector_store,
            search_type="similarity",
            search_kwargs={"k": top_k * 2},
        )

        # BM25 keyword retriever -- reuses stored documents.
        bm25_retriever = BM25Retriever.from_documents(
            vector_store.similarity_search(" ", k=50) if hasattr(vector_store, "similarity_search") else [],
        )
        bm25_retriever.k = top_k * 2

        self._ensemble = LC_EnsembleRetriever(
            retrievers=[semantic_retriever, bm25_retriever],
            weights=[0.5, 0.5],
        )
        self._vector_store = vector_store
        self._top_k = top_k

    async def retrieve(
        self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[RetrievalResult]:
        """Retrieve documents using both semantic and keyword signals.

        Args:
            query: Natural-language search string.
            top_k: Number of merged results to return.
            filters: Not supported by ensemble retriever; ignored.

        Returns:
            A list of ``RetrievalResult`` objects.
        """
        lc_docs = self._ensemble.invoke(query)[:top_k]
        return [RetrievalResult(document=doc, score=0.0) for doc in lc_docs]

    async def retrieve_by_id(self, doc_id: str) -> LCDocument | None:
        vc = self._vector_store
        if hasattr(vc, "get"):
            result = vc.get(ids=[doc_id])
            if result and result.get("documents"):
                docs = []
                for i, doc_content in enumerate(result["documents"]):
                    meta = result.get("metadatas", [{}])[i] if result.get("metadatas") else {}
                    docs.append(LCDocument(page_content=doc_content, metadata=meta))
                return docs[0] if docs else None
        return None
