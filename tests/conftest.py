"""Shared test fixtures.

Environment is forced to fully-offline mode (fake LLM + embeddings,
in-memory vector store, temp SQLite DB) before app modules are imported.
"""

from __future__ import annotations

import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="support-tests-")

os.environ.update(
    {
        "ENVIRONMENT": "development",
        "LLM_PROVIDER": "fake",
        "EMBEDDING_PROVIDER": "fake",
        "VECTOR_STORE": "memory",
        "DATABASE_URL": f"sqlite+aiosqlite:///{_TMP_DIR}/test.db",
        "SECRET_KEY": "test-secret-key-not-for-production",
        "ADMIN_EMAIL": "admin@acmetests.com",
        "ADMIN_PASSWORD": "test-admin-password",
        "RATE_LIMIT_PER_MINUTE": "10000",
        "LOG_JSON": "false",
        "EMAIL_ENABLED": "false",
    }
)

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def app():
    application = create_app()
    async with application.router.lifespan_context(application):
        yield application


@pytest_asyncio.fixture()
async def client(app) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client


@pytest_asyncio.fixture()
async def admin_token(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acmetests.com", "password": "test-admin-password"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}

