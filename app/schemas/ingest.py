"""Knowledge-base ingestion schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

SOURCE_TYPES = (
    "documentation",
    "faq",
    "help_center",
    "product_manual",
    "policy",
    "support_ticket",
    "knowledge_base",
)


class DocumentIn(BaseModel):
    content: str = Field(min_length=1)
    title: str = Field(default="Untitled", max_length=500)
    source_type: str = Field(default="documentation")
    source_url: str = Field(default="", max_length=2000)
    language: str = Field(default="en", max_length=16)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("source_type")
    @classmethod
    def _valid_source_type(cls, v: str) -> str:
        if v not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {SOURCE_TYPES}")
        return v


class IngestRequest(BaseModel):
    documents: list[DocumentIn] = Field(min_length=1, max_length=500)


class IngestResponse(BaseModel):
    indexed_documents: int
    indexed_chunks: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)


class SearchHit(BaseModel):
    content: str
    metadata: dict
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]
