"""Inbound webhooks for Slack and WhatsApp (Twilio) channels."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Header, Request
from fastapi.responses import JSONResponse

from app.api.deps import ContainerDep
from app.core.exceptions import AuthenticationError
from app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["channels"])


@router.post("/slack/events")
async def slack_events(
    request: Request,
    container: ContainerDep,
    x_slack_request_timestamp: str = Header(default=""),
    x_slack_signature: str = Header(default=""),
):
    """Slack Events API endpoint: responds to url_verification and app mentions."""
    body = await request.body()
    payload = await request.json()
    # URL verification handshake happens before signing is configured in dev.
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload.get("challenge", "")})
    if not container.slack.verify_signature(
        x_slack_request_timestamp, x_slack_signature, body
    ):
        raise AuthenticationError("Invalid Slack signature")
    event = payload.get("event", {})
    if event.get("type") in ("app_mention", "message") and not event.get("bot_id"):
        text = str(event.get("text", "")).strip()
        if text:
            response = await container.workflow.run(
                ChatRequest(message=text, channel="slack")
            )
            await container.slack.notify(response.answer)
    return JSONResponse({"ok": True})


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    container: ContainerDep,
    Body: str = Form(default=""),
    From: str = Form(default=""),
):
    """Twilio WhatsApp inbound webhook (application/x-www-form-urlencoded)."""
    text = Body.strip()
    sender = From.removeprefix("whatsapp:")
    if not text:
        return JSONResponse({"ok": True})
    response = await container.workflow.run(
        ChatRequest(message=text, channel="whatsapp")
    )
    if sender:
        try:
            await container.whatsapp.send(sender, response.answer)
        except Exception:
            logger.exception("WhatsApp reply failed")
    return JSONResponse({"ok": True, "conversation_id": response.conversation_id})
