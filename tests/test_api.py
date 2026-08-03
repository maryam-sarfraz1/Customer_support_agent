"""Integration tests for the REST API (offline: fake LLM + embeddings)."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.asyncio

SAMPLE_DOCS = {
    "documents": [
        {
            "title": "Refund Policy",
            "source_type": "policy",
            "content": (
                "Customers may request a full refund within 30 days of purchase. "
                "Refunds are processed to the original payment method within 5 "
                "business days. Digital products are refundable only if unused."
            ),
        },
        {
            "title": "Password Reset FAQ",
            "source_type": "faq",
            "content": (
                "To reset your password, click 'Forgot password' on the login "
                "page. A reset link is emailed to you and expires after 1 hour."
            ),
        },
    ]
}


async def test_health(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_openapi_available(client: httpx.AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/v1/chat" in resp.json()["paths"]


async def test_register_login_me_flow(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer@acmetests.com",
            "password": "customer-pass-123",
            "full_name": "Test Customer",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "customer"

    # Duplicate registration conflicts.
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "customer@acmetests.com", "password": "customer-pass-123"},
    )
    assert resp.status_code == 409

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "customer@acmetests.com", "password": "customer-pass-123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "customer@acmetests.com"


async def test_login_wrong_password(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acmetests.com", "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_rbac_customer_cannot_ingest(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "lowpriv@acmetests.com", "password": "lowpriv-pass-123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "lowpriv@acmetests.com", "password": "lowpriv-pass-123"},
    )
    token = login.json()["access_token"]
    resp = await client.post(
        "/api/v1/knowledge/ingest",
        json=SAMPLE_DOCS,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_ingest_requires_auth(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/knowledge/ingest", json=SAMPLE_DOCS)
    assert resp.status_code == 401


async def test_ingest_and_chat_with_citations(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/knowledge/ingest", json=SAMPLE_DOCS, headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["indexed_documents"] == 2
    assert body["indexed_chunks"] >= 2

    resp = await client.post(
        "/api/v1/knowledge/search",
        json={"query": "refund policy", "top_k": 3},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["hits"]) >= 1

    resp = await client.post(
        "/api/v1/chat",
        json={"message": "What is your refund policy?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert data["conversation_id"]
    assert data["confidence"] >= 0.5
    assert not data["escalated"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["source"]


async def test_conversation_memory_continuity(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/knowledge/ingest", json=SAMPLE_DOCS, headers=admin_headers
    )
    first = (
        await client.post("/api/v1/chat", json={"message": "How do I reset my password?"})
    ).json()
    second = (
        await client.post(
            "/api/v1/chat",
            json={
                "message": "How long is that link valid?",
                "conversation_id": first["conversation_id"],
            },
        )
    ).json()
    assert second["conversation_id"] == first["conversation_id"]
    assert second["message_id"] != first["message_id"]


async def test_human_handoff_creates_ticket(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/chat",
        json={
            "message": "I want to speak to a real person please",
            "customer_email": "upset@acmetests.com",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["escalated"] is True
    assert data["ticket_id"]
    assert data["email_draft"]

    resp = await client.get(
        f"/api/v1/tickets/{data['ticket_id']}", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["customer_email"] == "upset@acmetests.com"


async def test_complaint_opens_ticket(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/knowledge/ingest", json=SAMPLE_DOCS, headers=admin_headers
    )
    resp = await client.post(
        "/api/v1/chat",
        json={"message": "I want a refund, my order arrived broken!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "complaint"
    assert data["ticket_id"]


async def test_ticket_crud(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    created = (
        await client.post(
            "/api/v1/tickets",
            json={"subject": "Manual ticket", "description": "details"},
            headers=admin_headers,
        )
    ).json()
    assert created["status"] == "open"

    updated = (
        await client.patch(
            f"/api/v1/tickets/{created['id']}",
            json={"status": "resolved", "priority": "low"},
            headers=admin_headers,
        )
    ).json()
    assert updated["status"] == "resolved"
    assert updated["priority"] == "low"

    listed = (
        await client.get("/api/v1/tickets?status=resolved", headers=admin_headers)
    ).json()
    assert any(t["id"] == created["id"] for t in listed)

    missing = await client.get("/api/v1/tickets/does-not-exist", headers=admin_headers)
    assert missing.status_code == 404


async def test_feedback_and_analytics(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    chat = (await client.post("/api/v1/chat", json={"message": "hello"})).json()
    resp = await client.post(
        "/api/v1/feedback",
        json={
            "conversation_id": chat["conversation_id"],
            "message_id": chat["message_id"],
            "rating": 5,
            "comment": "great answer",
        },
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversations"] >= 1
    assert data["messages"] >= 2
    assert data["avg_feedback_rating"] is not None


async def test_admin_dashboard_served(client: httpx.AsyncClient) -> None:
    resp = await client.get("/admin")
    assert resp.status_code == 200
    assert "Support Ops" in resp.text


async def test_customer_chat_page_served(client: httpx.AsyncClient) -> None:
    resp = await client.get("/chat")
    assert resp.status_code == 200
    assert "support" in resp.text.lower()

    resp = await client.get("/widget.js")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/javascript")
    assert "sw-bubble" in resp.text


async def test_root_redirects_to_chat(client: httpx.AsyncClient) -> None:
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302, 307)
    assert resp.headers["location"] == "/chat"


async def test_whatsapp_webhook(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/channels/whatsapp/webhook",
        data={"Body": "What is your refund policy?", "From": "whatsapp:+15551234567"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_slack_url_verification(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/channels/slack/events",
        json={"type": "url_verification", "challenge": "abc123"},
    )
    assert resp.status_code == 200
    assert resp.json()["challenge"] == "abc123"


async def test_validation_error_shape(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/chat", json={"message": ""})
    assert resp.status_code == 422

