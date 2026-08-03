"""Chat and feedback endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import ContainerDep
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, container: ContainerDep) -> ChatResponse:
    """Run one turn of the multi-agent support workflow."""
    return await container.workflow.run(request)


@router.post(
    "/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED
)
async def submit_feedback(
    request: FeedbackRequest, container: ContainerDep
) -> FeedbackResponse:
    fb = await container.feedback.record(request)
    return FeedbackResponse(id=fb.id)
