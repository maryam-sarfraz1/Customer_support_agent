"""Aggregate v1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analytics, auth, channels, chat, ingest, tickets

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(ingest.router)
api_router.include_router(tickets.router)
api_router.include_router(analytics.router)
api_router.include_router(channels.router)
