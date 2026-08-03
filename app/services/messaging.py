"""Slack and WhatsApp (Twilio) outbound messaging."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time

import httpx

from app.core.config import Settings
from app.core.exceptions import IntegrationError

logger = logging.getLogger(__name__)


class SlackService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self._settings.slack_webhook_url)

    async def notify(self, text: str) -> bool:
        """Post a message to the configured Slack incoming webhook."""
        if not self.enabled:
            logger.info("Slack disabled; skipping notification: %s", text[:120])
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._settings.slack_webhook_url, json={"text": text}
                )
                resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            raise IntegrationError(f"Slack notification failed: {exc}") from exc

    def verify_signature(
        self, timestamp: str, signature: str, body: bytes
    ) -> bool:
        """Verify a Slack events request signature (v0 scheme)."""
        secret = self._settings.slack_signing_secret
        if not secret:
            return False
        try:
            if abs(time.time() - float(timestamp)) > 60 * 5:
                return False
        except ValueError:
            return False
        base = f"v0:{timestamp}:".encode() + body
        expected = (
            "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
        )
        return hmac.compare_digest(expected, signature)


class WhatsAppService:
    """Sends WhatsApp messages through the Twilio REST API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        s = self._settings
        return bool(s.twilio_account_sid and s.twilio_auth_token and s.twilio_whatsapp_from)

    async def send(self, to: str, body: str) -> bool:
        if not self.enabled:
            logger.info("WhatsApp disabled; skipping send to %s", to)
            return False
        s = self._settings
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{s.twilio_account_sid}/Messages.json"
        )
        data = {
            "From": f"whatsapp:{s.twilio_whatsapp_from}",
            "To": f"whatsapp:{to}",
            "Body": body[:1600],
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    url, data=data, auth=(s.twilio_account_sid, s.twilio_auth_token)
                )
                resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            raise IntegrationError(f"WhatsApp send failed: {exc}") from exc
