"""Customer feedback collection."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Feedback
from app.schemas.chat import FeedbackRequest

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(self, data: FeedbackRequest) -> Feedback:
        async with self._session_factory() as session:
            fb = Feedback(
                conversation_id=data.conversation_id,
                message_id=data.message_id,
                rating=data.rating,
                comment=data.comment,
            )
            session.add(fb)
            await session.commit()
            await session.refresh(fb)
            logger.info("Recorded feedback %s rating=%d", fb.id, fb.rating)
            return fb
