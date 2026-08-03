"""Outbound email via SMTP (stdlib, run in a worker thread to stay async)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings
from app.core.exceptions import IntegrationError

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self._settings.email_enabled and self._settings.smtp_host)

    async def send(self, to: str, subject: str, body: str) -> bool:
        """Send an email. Returns False (and logs) when email is not configured."""
        if not self.enabled:
            logger.info(
                "Email disabled; skipping send to %s (subject=%r)", to, subject[:80]
            )
            return False
        try:
            await asyncio.to_thread(self._send_sync, to, subject, body)
            return True
        except Exception as exc:
            raise IntegrationError(f"Failed to send email: {exc}") from exc

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        settings = self._settings
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Sent email to %s", to)
