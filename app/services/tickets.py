"""Support ticket management."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import NotFoundError
from app.db.models import Ticket, TicketPriority, TicketStatus
from app.schemas.tickets import TicketCreate, TicketUpdate

logger = logging.getLogger(__name__)


class TicketService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, data: TicketCreate) -> Ticket:
        async with self._session_factory() as session:
            ticket = Ticket(
                subject=data.subject[:500],
                description=data.description,
                priority=data.priority,
                category=data.category,
                customer_email=data.customer_email,
                conversation_id=data.conversation_id,
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            logger.info("Created ticket %s (%s)", ticket.id, ticket.subject[:80])
            return ticket

    async def get(self, ticket_id: str) -> Ticket:
        async with self._session_factory() as session:
            ticket = await session.get(Ticket, ticket_id)
            if ticket is None:
                raise NotFoundError(f"Ticket {ticket_id} not found")
            return ticket

    async def list(
        self,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Ticket]:
        async with self._session_factory() as session:
            stmt = select(Ticket).order_by(Ticket.created_at.desc())
            if status is not None:
                stmt = stmt.where(Ticket.status == status)
            if priority is not None:
                stmt = stmt.where(Ticket.priority == priority)
            stmt = stmt.limit(min(limit, 200)).offset(max(offset, 0))
            return list((await session.execute(stmt)).scalars().all())

    async def update(self, ticket_id: str, data: TicketUpdate) -> Ticket:
        async with self._session_factory() as session:
            ticket = await session.get(Ticket, ticket_id)
            if ticket is None:
                raise NotFoundError(f"Ticket {ticket_id} not found")
            for field, value in data.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(ticket, field, value)
            await session.commit()
            await session.refresh(ticket)
            return ticket

    async def escalate(self, ticket_id: str) -> Ticket:
        return await self.update(
            ticket_id, TicketUpdate(status=TicketStatus.ESCALATED)
        )
