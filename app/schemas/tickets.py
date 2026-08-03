"""Ticket schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=16000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str = Field(default="general", max_length=64)
    customer_email: str = Field(default="", max_length=255)
    conversation_id: str | None = None


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: str | None = None
    category: str | None = None


class TicketOut(BaseModel):
    id: str
    conversation_id: str | None
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str
    customer_email: str
    assignee_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
