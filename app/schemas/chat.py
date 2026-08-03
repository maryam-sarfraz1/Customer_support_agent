"""Chat request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    index: int = Field(ge=1, description="Citation marker used in the answer, e.g. [1].")
    source: str = Field(description="Source document identifier or title.")
    snippet: str = Field(default="", description="Relevant excerpt from the source.")
    score: float | None = Field(default=None, description="Retrieval relevance score.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = Field(
        default=None, description="Continue an existing conversation."
    )
    channel: str = Field(default="web")
    customer_email: str = Field(default="", max_length=255)
    language: str | None = Field(
        default=None, description="Force a response language (ISO code). Auto-detected if omitted."
    )


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    citations: list[Citation] = []
    confidence: float = 0.0
    intent: str = "question"
    language: str = "en"
    escalated: bool = False
    ticket_id: str | None = None
    email_draft: str | None = None
    latency_ms: int = 0


class FeedbackRequest(BaseModel):
    conversation_id: str | None = None
    message_id: str | None = None
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=4000)


class FeedbackResponse(BaseModel):
    id: str
    status: str = "recorded"
