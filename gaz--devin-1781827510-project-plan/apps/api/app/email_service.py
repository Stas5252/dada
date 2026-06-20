import asyncio
import logging
from email.message import EmailMessage

import aiosmtplib

from app.settings import get_settings

logger = logging.getLogger(__name__)


async def _send_email_async(to_email: str, subject: str, html_content: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning(f"Mock email sent to {to_email}")
        logger.warning(f"Content: {html_content}")
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")


def send_verification_email(email: str, token: str) -> None:
    link = f"https://your-domain.com/verify-email?token={token}"
    html = (
        "<p>Please verify your email by clicking the link below:</p>"
        f"<p><a href='{link}'>{link}</a></p>"
    )
    asyncio.create_task(_send_email_async(email, "Verify your CallForce account", html))


def send_password_reset_email(email: str, token: str) -> None:
    link = f"https://your-domain.com/reset-password?token={token}"
    html = (
        "<p>Reset your password by clicking the link below:</p>"
        f"<p><a href='{link}'>{link}</a></p>"
    )
    asyncio.create_task(_send_email_async(email, "Reset your CallForce password", html))
