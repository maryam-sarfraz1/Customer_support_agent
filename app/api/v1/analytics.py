"""Analytics endpoints (staff only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep, StaffUser

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(
    _: StaffUser,
    container: ContainerDep,
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Conversation, escalation, ticket, latency, and satisfaction metrics."""
    return await container.analytics.overview(days=days)
