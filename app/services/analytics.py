"""Conversation and feedback analytics."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Conversation, Feedback, Message, Ticket, TicketStatus

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def overview(self, days: int = 30) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))
        async with self._session_factory() as session:
            conversations = await self._count(
                session, select(func.count(Conversation.id)).where(
                    Conversation.created_at >= since
                )
            )
            messages = await self._count(
                session, select(func.count(Message.id)).where(
                    Message.created_at >= since
                )
            )
            escalations = await self._count(
                session,
                select(func.count(Message.id)).where(
                    Message.created_at >= since, Message.escalated == 1
                ),
            )
            open_tickets = await self._count(
                session,
                select(func.count(Ticket.id)).where(
                    Ticket.status.in_([TicketStatus.OPEN, TicketStatus.ESCALATED])
                ),
            )
            avg_confidence = (
                await session.execute(
                    select(func.avg(Message.confidence)).where(
                        Message.created_at >= since,
                        Message.confidence.is_not(None),
                    )
                )
            ).scalar()
            avg_latency = (
                await session.execute(
                    select(func.avg(Message.latency_ms)).where(
                        Message.created_at >= since,
                        Message.latency_ms.is_not(None),
                    )
                )
            ).scalar()
            avg_rating = (
                await session.execute(
                    select(func.avg(Feedback.rating)).where(
                        Feedback.created_at >= since
                    )
                )
            ).scalar()
            intents = (
                await session.execute(
                    select(Message.intent, func.count(Message.id))
                    .where(Message.created_at >= since, Message.intent.is_not(None))
                    .group_by(Message.intent)
                )
            ).all()

        assistant_msgs = await self._assistant_message_count(since)
        deflection = (
            1.0 - (escalations / assistant_msgs) if assistant_msgs else None
        )
        return {
            "window_days": days,
            "conversations": conversations,
            "messages": messages,
            "escalations": escalations,
            "open_tickets": open_tickets,
            "avg_confidence": round(avg_confidence, 3) if avg_confidence else None,
            "avg_latency_ms": round(avg_latency, 1) if avg_latency else None,
            "avg_feedback_rating": round(avg_rating, 2) if avg_rating else None,
            "deflection_rate": round(deflection, 3) if deflection is not None else None,
            "intent_breakdown": {intent: count for intent, count in intents},
        }

    async def _assistant_message_count(self, since: datetime) -> int:
        async with self._session_factory() as session:
            return await self._count(
                session,
                select(func.count(Message.id)).where(
                    Message.created_at >= since, Message.role == "assistant"
                ),
            )

    @staticmethod
    async def _count(session: AsyncSession, stmt) -> int:
        return int((await session.execute(stmt)).scalar() or 0)
