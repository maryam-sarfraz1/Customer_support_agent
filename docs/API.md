# API Reference

Base URL: `http://localhost:8000` · All bodies are JSON unless noted.
Interactive docs: `/docs` (Swagger UI), machine-readable spec: `/openapi.json`.

Authentication: `Authorization: Bearer <JWT>` from `/api/v1/auth/login`.
Roles: `admin` (everything), `agent` (staff endpoints), `customer` (self only).

Errors use a consistent envelope:

```json
{"error": {"code": "not_found", "message": "Ticket abc not found"}}
```

---

## System

### GET /health
Liveness probe. → `{"status": "ok", "version": "1.0.0"}`

### GET /admin
HTML admin dashboard (sign in with a staff account).

---

## Auth

### POST /api/v1/auth/register → 201
```json
{"email": "jane@example.com", "password": "min-8-chars", "full_name": "Jane"}
```
New users get the `customer` role.

### POST /api/v1/auth/login
```json
{"email": "...", "password": "..."}
```
→ `{"access_token": "...", "token_type": "bearer"}`

### GET /api/v1/auth/me — current user profile.
### GET /api/v1/auth/users — admin: list users.
### PATCH /api/v1/auth/users/{id}/role — admin: `{"role": "agent"}`

---

## Chat

### POST /api/v1/chat
Runs the full multi-agent workflow for one turn.

Request:
```json
{
  "message": "What is your refund policy?",
  "conversation_id": null,
  "channel": "web",
  "customer_email": "jane@example.com",
  "language": null
}
```

Response:
```json
{
  "conversation_id": "…",
  "message_id": "…",
  "answer": "You can request a refund within 30 days… [1]",
  "citations": [{"index": 1, "source": "Refund Policy", "snippet": "…", "score": 0.87}],
  "confidence": 0.9,
  "intent": "question",
  "language": "en",
  "escalated": false,
  "ticket_id": null,
  "email_draft": null,
  "latency_ms": 812
}
```

`escalated: true` means a human was looped in; `ticket_id` is set whenever a
ticket was auto-created; `email_draft` contains the Email Agent's follow-up.
Pass `conversation_id` back to continue with memory.

### POST /api/v1/feedback → 201
```json
{"conversation_id": "…", "message_id": "…", "rating": 5, "comment": "Great"}
```

---

## Knowledge base (staff)

### POST /api/v1/knowledge/ingest
```json
{
  "documents": [{
    "title": "Refund Policy",
    "content": "…full text…",
    "source_type": "policy",
    "source_url": "https://…",
    "language": "en",
    "metadata": {"version": "2024-06"}
  }]
}
```
`source_type`: `documentation | faq | help_center | product_manual | policy |
support_ticket | knowledge_base`.
→ `{"indexed_documents": 1, "indexed_chunks": 3}`

### POST /api/v1/knowledge/search
`{"query": "refund", "top_k": 5}` → scored chunks with metadata.

---

## Tickets (staff)

- `POST /api/v1/tickets` → 201 — `{subject, description, priority, category, customer_email, conversation_id}`
- `GET /api/v1/tickets?status=open&priority=high&limit=50&offset=0`
- `GET /api/v1/tickets/{id}`
- `PATCH /api/v1/tickets/{id}` — any of `{status, priority, assignee_id, category}`

`status`: `open | in_progress | escalated | resolved | closed` ·
`priority`: `low | medium | high | urgent`

---

## Analytics (staff)

### GET /api/v1/analytics/overview?days=30
```json
{
  "window_days": 30, "conversations": 128, "messages": 512,
  "escalations": 9, "open_tickets": 4,
  "avg_confidence": 0.83, "avg_latency_ms": 640.2,
  "avg_feedback_rating": 4.6, "deflection_rate": 0.965,
  "intent_breakdown": {"question": 220, "complaint": 18}
}
```

---

## Channels

### POST /api/v1/channels/slack/events
Slack Events API endpoint. Handles `url_verification` challenges; all other
events require a valid `X-Slack-Signature` (v0 HMAC with your signing secret).
App mentions / messages are answered through the workflow and posted back via
the incoming webhook.

### POST /api/v1/channels/whatsapp/webhook
Twilio inbound webhook (`application/x-www-form-urlencoded`, fields `Body`,
`From`). The reply is sent back over WhatsApp via the Twilio REST API when
Twilio credentials are configured.
