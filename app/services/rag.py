"""RAG ingestion pipeline: chunking, metadata, indexing, retrieval."""

from __future__ import annotations

import hashlib
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings
from app.schemas.ingest import DocumentIn
from app.services.vectorstore import VectorStoreService

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, settings: Settings, store: VectorStoreService) -> None:
        self._settings = settings
        self._store = store
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    async def ingest(self, documents: list[DocumentIn]) -> tuple[int, int]:
        """Chunk and index documents. Returns (doc_count, chunk_count)."""
        chunks: list[Document] = []
        for doc in documents:
            doc_id = hashlib.sha256(
                f"{doc.title}:{doc.content[:200]}".encode()
            ).hexdigest()[:16]
            pieces = self._splitter.split_text(doc.content)
            for i, piece in enumerate(pieces):
                chunks.append(
                    Document(
                        page_content=piece,
                        metadata={
                            "doc_id": doc_id,
                            "chunk": i,
                            "title": doc.title,
                            "source_type": doc.source_type,
                            "source_url": doc.source_url,
                            "language": doc.language,
                            **doc.metadata,
                        },
                    )
                )
        indexed = await self._store.add_documents(chunks)
        logger.info(
            "Ingested %d documents as %d chunks", len(documents), indexed
        )
        return len(documents), indexed

    async def retrieve(
        self, query: str, top_k: int | None = None
    ) -> list[tuple[Document, float]]:
        k = top_k or self._settings.retrieval_top_k
        return await self._store.search(query, top_k=k)
