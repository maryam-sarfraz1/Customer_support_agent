"""Vector store abstraction: ChromaDB (persistent) or in-memory fallback."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore, VectorStore

from app.core.config import Settings
from app.core.exceptions import RetrievalError

logger = logging.getLogger(__name__)


def build_vector_store(settings: Settings, embeddings: Embeddings) -> VectorStore:
    if settings.vector_store == "chroma":
        try:
            from langchain_chroma import Chroma

            return Chroma(
                collection_name=settings.collection_name,
                embedding_function=embeddings,
                persist_directory=settings.chroma_persist_dir,
            )
        except ImportError:
            logger.warning(
                "langchain-chroma not installed; falling back to in-memory vector store."
            )
    return InMemoryVectorStore(embedding=embeddings)


class VectorStoreService:
    """Async wrapper with error handling around a LangChain VectorStore."""

    def __init__(self, store: VectorStore) -> None:
        self._store = store
        self._lock = asyncio.Lock()

    async def add_documents(self, documents: list[Document]) -> int:
        if not documents:
            return 0
        try:
            async with self._lock:
                await self._store.aadd_documents(documents)
            return len(documents)
        except Exception as exc:  # pragma: no cover - backend-specific failures
            raise RetrievalError(f"Failed to index documents: {exc}") from exc

    async def search(
        self, query: str, top_k: int = 5
    ) -> list[tuple[Document, float]]:
        """Return (document, relevance_score) pairs, higher score = more relevant."""
        try:
            try:
                results = await self._store.asimilarity_search_with_relevance_scores(
                    query, k=top_k
                )
            except NotImplementedError:
                # Some backends (e.g. InMemoryVectorStore) only expose raw
                # similarity scores; cosine similarity is already ~[0, 1].
                results = await self._store.asimilarity_search_with_score(
                    query, k=top_k
                )
        except Exception as exc:
            raise RetrievalError(f"Vector search failed: {exc}") from exc
        # Clamp scores into [0, 1]; some backends can return values slightly outside.
        return [(doc, max(0.0, min(1.0, score))) for doc, score in results]
