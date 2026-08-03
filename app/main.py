"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app import __version__
from app.api.admin_dashboard import DASHBOARD_HTML
from app.api.chat_page import render_chat_html, render_widget_js
from app.api.container import build_container
from app.api.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import dispose_db, get_session_factory, init_db

logger = logging.getLogger(__name__)


async def _ensure_admin_user() -> None:
    """Bootstrap the initial admin account from environment configuration."""
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        existing = (
            await session.execute(
                select(User).where(User.email == settings.admin_email)
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                User(
                    email=settings.admin_email,
                    full_name="Administrator",
                    hashed_password=hash_password(settings.admin_password),
                    role=UserRole.ADMIN,
                )
            )
            await session.commit()
            logger.info("Bootstrapped admin user %s", settings.admin_email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    if (
        settings.environment == "production"
        and settings.secret_key == "change-me-in-production"
    ):
        raise RuntimeError("SECRET_KEY must be set in production")
    await init_db()
    await _ensure_admin_user()
    app.state.container = build_container(settings)
    logger.info(
        "Started %s v%s (provider=%s, vector_store=%s)",
        settings.app_name,
        __version__,
        settings.llm_provider,
        settings.vector_store,
    )
    yield
    await dispose_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "AI-powered customer support with RAG, LangGraph multi-agent "
            "workflows, ticketing, escalation, and omni-channel integrations."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/chat")

    @app.get("/chat", response_class=HTMLResponse, include_in_schema=False)
    async def chat_page() -> str:
        return render_chat_html(get_settings())

    @app.get("/widget.js", include_in_schema=False)
    async def widget_js() -> Response:
        return Response(
            content=render_widget_js(get_settings()),
            media_type="application/javascript",
        )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
    async def admin_dashboard() -> str:
        return DASHBOARD_HTML

    return app


app = create_app()
