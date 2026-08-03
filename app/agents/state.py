"""Shared LangGraph state for the support workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class RetrievedChunk(TypedDict):
    content: str
    title: str
    source_type: str
    source_url: str
    score: float


class SupportState(TypedDict, total=False):
    # Input
    conversation_id: str
    message: str
    channel: str
    customer_email: str
    forced_language: str | None
    history: list[dict[str, str]]

    # Query understanding
    intent: str  # question | complaint | request_human | chitchat
    language: str
    rewritten_query: str
    sentiment: str  # positive | neutral | negative
    category: str

    # Retrieval
    retrieved: list[RetrievedChunk]
    retrieval_attempts: int

    # Generation
    answer: str
    citations: list[dict[str, Any]]

    # Verification
    confidence: float
    grounded: bool
    critic_issues: list[str]

    # Actions
    needs_escalation: bool
    escalation_reason: str
    ticket_id: str | None
    email_draft: str | None
