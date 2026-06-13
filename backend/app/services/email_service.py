import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("uvicorn.error")


def _send_smtp(recipient: str, subject: str, body: str) -> None:
    settings = get_settings()
    logger.info(
        "SMTP connecting host=%s port=%s ssl=%s starttls=%s auth=%s sender=%s recipient=%s",
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_use_ssl,
        settings.smtp_use_tls,
        bool(settings.smtp_username),
        settings.email_from,
        recipient,
    )
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        logger.info("SMTP connection established host=%s port=%s", settings.smtp_host, settings.smtp_port)
        if settings.smtp_use_tls and not settings.smtp_use_ssl:
            logger.info("SMTP starting TLS host=%s", settings.smtp_host)
            server.starttls()
        if settings.smtp_username:
            logger.info("SMTP authenticating username=%s", settings.smtp_username)
            server.login(settings.smtp_username, settings.smtp_password)
        logger.info("SMTP sending message recipient=%s subject=%s", recipient, subject)
        server.send_message(message)
    logger.info("SMTP message accepted recipient=%s", recipient)


async def send_verification_email(
    recipient: str, display_name: str, verification_url: str, verification_code: str
) -> None:
    settings = get_settings()
    body = (
        f"Hello {display_name},\n\n"
        "Confirm your Momentum account by opening this link:\n"
        f"{verification_url}\n\n"
        "Or enter this confirmation code in the app:\n"
        f"{verification_code}\n\n"
        f"The link expires in {settings.email_verification_expire_hours} hours."
    )
    if settings.email_delivery_mode == "smtp":
        if not settings.smtp_host:
            raise RuntimeError("SMTP_HOST must be configured when EMAIL_DELIVERY_MODE=smtp.")
        try:
            await asyncio.to_thread(
                _send_smtp,
                recipient,
                "Confirm your Momentum account",
                body,
            )
        except Exception:
            logger.exception(
                "SMTP delivery failed host=%s port=%s recipient=%s",
                settings.smtp_host,
                settings.smtp_port,
                recipient,
            )
            raise
        return
    logger.warning("Development email verification link for %s: %s", recipient, verification_url)
