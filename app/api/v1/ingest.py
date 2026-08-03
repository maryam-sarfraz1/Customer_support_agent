"""Knowledge-base ingestion and search endpoints (staff only)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep, StaffUser
from app.schemas.ingest import (
    IngestRequest,
    IngestResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge-base"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest, _: StaffUser, container: ContainerDep
) -> IngestResponse:
    """Index documents (docs, FAQs, manuals, policies, tickets, KB articles)."""
    docs, chunks = await container.rag.ingest(request.documents)
    return IngestResponse(indexed_documents=docs, indexed_chunks=chunks)


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest, _: StaffUser, container: ContainerDep
) -> SearchResponse:
    """Directly query the vector store (debugging / relevance tuning)."""
    results = await container.rag.retrieve(request.query, top_k=request.top_k)
    return SearchResponse(
        hits=[
            SearchHit(content=doc.page_content, metadata=doc.metadata, score=score)
            for doc, score in results
        ]
    )
