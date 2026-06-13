import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _send_smtp(recipient: str, subject: str, body: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


async def send_verification_email(
    recipient: str, display_name: str, verification_url: str
) -> None:
    settings = get_settings()
    body = (
        f"Hello {display_name},\n\n"
        "Confirm your Momentum account by opening this link:\n"
        f"{verification_url}\n\n"
        f"The link expires in {settings.email_verification_expire_hours} hours."
    )
    if settings.email_delivery_mode == "smtp":
        if not settings.smtp_host:
            raise RuntimeError("SMTP_HOST must be configured when EMAIL_DELIVERY_MODE=smtp.")
        await asyncio.to_thread(
            _send_smtp,
            recipient,
            "Confirm your Momentum account",
            body,
        )
        return
    logger.warning("Development email verification link for %s: %s", recipient, verification_url)
