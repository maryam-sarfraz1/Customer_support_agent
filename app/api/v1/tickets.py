"""Ticket management endpoints (staff only)."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import ContainerDep, StaffUser
from app.db.models import TicketPriority, TicketStatus
from app.schemas.tickets import TicketCreate, TicketOut, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate, _: StaffUser, container: ContainerDep
) -> TicketOut:
    return TicketOut.model_validate(await container.tickets.create(data))


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    _: StaffUser,
    container: ContainerDep,
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TicketOut]:
    tickets = await container.tickets.list(
        status=status_filter, priority=priority, limit=limit, offset=offset
    )
    return [TicketOut.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: str, _: StaffUser, container: ContainerDep
) -> TicketOut:
    return TicketOut.model_validate(await container.tickets.get(ticket_id))


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: str, data: TicketUpdate, _: StaffUser, container: ContainerDep
) -> TicketOut:
    return TicketOut.model_validate(await container.tickets.update(ticket_id, data))
