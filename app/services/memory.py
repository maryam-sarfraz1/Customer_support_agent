"""Conversation memory backed by the relational database."""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Conversation, Message

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 12


class ConversationMemory:
    """Persists and recalls conversation turns."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_or_create_conversation(
        self,
        conversation_id: str | None,
        channel: str = "web",
        user_id: str | None = None,
    ) -> Conversation:
        async with self._session_factory() as session:
            if conversation_id:
                conv = await session.get(Conversation, conversation_id)
                if conv is not None:
                    return conv
            conv = Conversation(channel=channel, user_id=user_id)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            return conv

    async def history(self, conversation_id: str) -> list[dict[str, str]]:
        """Recent turns as [{'role': ..., 'content': ...}] oldest-first."""
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at.desc())
                    .limit(MAX_HISTORY_MESSAGES)
                )
            ).scalars().all()
        return [
            {"role": m.role, "content": m.content} for m in reversed(rows)
        ]

    async def append_user_message(
        self, conversation_id: str, content: str
    ) -> Message:
        async with self._session_factory() as session:
            msg = Message(
                conversation_id=conversation_id, role="user", content=content
            )
            session.add(msg)
            await session.commit()
            await session.refresh(msg)
            return msg

    async def append_assistant_message(
        self,
        conversation_id: str,
        content: str,
        *,
        intent: str | None = None,
        confidence: float | None = None,
        escalated: bool = False,
        citations: list[dict] | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        async with self._session_factory() as session:
            msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                intent=intent,
                confidence=confidence,
                escalated=1 if escalated else 0,
                citations_json=json.dumps(citations) if citations else None,
                latency_ms=latency_ms,
            )
            session.add(msg)
            await session.commit()
            await session.refresh(msg)
            return msg
