import asyncio
import logging
from email.message import EmailMessage

import aiosmtplib

from app.settings import get_settings

logger = logging.getLogger(__name__)


def _brand_html(title: str, body_html: str) -> str:
    """Wrap content in a branded CallForce email template."""
    return f"""\
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#09090b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#09090b;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#18181b;border-radius:16px;border:1px solid rgba(255,255,255,0.05);overflow:hidden;">
        <!-- Header -->
        <tr><td style="padding:32px 40px 24px;border-bottom:1px solid rgba(255,255,255,0.05);">
          <div style="font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">
            ⚡ CallForce
          </div>
        </td></tr>
        <!-- Content -->
        <tr><td style="padding:32px 40px;">
          <h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#ffffff;line-height:1.3;">{title}</h1>
          {body_html}
        </td></tr>
        <!-- Footer -->
        <tr><td style="padding:24px 40px 32px;border-top:1px solid rgba(255,255,255,0.05);">
          <p style="margin:0;font-size:12px;color:#71717a;line-height:1.5;">
            © 2026 CallForce — AI-платформа поддержки клиентов<br>
            Это автоматическое письмо. Если вы не совершали это действие, проигнорируйте его.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _action_button(url: str, label: str) -> str:
    """Generate a branded CTA button for emails."""
    return (
        f'<table cellpadding="0" cellspacing="0" style="margin:24px 0;">'
        f'<tr><td style="background:linear-gradient(135deg,#10b981,#8b5cf6);border-radius:10px;padding:14px 32px;">'
        f'<a href="{url}" style="color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;display:inline-block;">'
        f'{label}</a></td></tr></table>'
    )


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


def _get_frontend_url() -> str:
    """Get the frontend base URL for email links."""
    settings = get_settings()
    # Use API public URL as base, but replace port for frontend if local
    base = settings.api_public_url
    if "localhost:8000" in base:
        return base.replace(":8000", ":3000")
    # In production, frontend is usually on the same domain without port
    return base.replace("/api", "").rstrip("/")


def send_verification_email(email: str, token: str) -> None:
    frontend_url = _get_frontend_url()
    link = f"{frontend_url}/verify-email?token={token}"
    body = (
        '<p style="margin:0 0 16px;font-size:15px;color:#a1a1aa;line-height:1.6;">'
        "Спасибо за регистрацию в CallForce! Подтвердите ваш email, "
        "нажав на кнопку ниже:</p>"
        + _action_button(link, "Подтвердить email")
        + '<p style="margin:0;font-size:13px;color:#52525b;line-height:1.5;">'
        "Или скопируйте ссылку:<br>"
        f'<a href="{link}" style="color:#8b5cf6;word-break:break-all;">{link}</a></p>'
    )
    html = _brand_html("Подтвердите ваш email", body)
    asyncio.create_task(_send_email_async(email, "Подтвердите email — CallForce", html))


def send_password_reset_email(email: str, token: str) -> None:
    frontend_url = _get_frontend_url()
    link = f"{frontend_url}/reset-password?token={token}"
    body = (
        '<p style="margin:0 0 16px;font-size:15px;color:#a1a1aa;line-height:1.6;">'
        "Вы запросили сброс пароля для вашего аккаунта CallForce. "
        "Нажмите кнопку ниже, чтобы установить новый пароль:</p>"
        + _action_button(link, "Сбросить пароль")
        + '<p style="margin:0;font-size:13px;color:#52525b;line-height:1.5;">'
        "Ссылка действительна 1 час. Если вы не запрашивали сброс пароля, "
        "просто проигнорируйте это письмо.</p>"
    )
    html = _brand_html("Сброс пароля", body)
    asyncio.create_task(_send_email_async(email, "Сброс пароля — CallForce", html))


def send_team_invite_email(email: str, inviter_name: str, company_name: str, invite_token: str) -> None:
    frontend_url = _get_frontend_url()
    link = f"{frontend_url}/register?invite={invite_token}"
    body = (
        f'<p style="margin:0 0 16px;font-size:15px;color:#a1a1aa;line-height:1.6;">'
        f"<strong style='color:#ffffff;'>{inviter_name}</strong> приглашает вас "
        f"присоединиться к команде <strong style='color:#ffffff;'>{company_name}</strong> "
        f"на платформе CallForce.</p>"
        + _action_button(link, "Принять приглашение")
        + '<p style="margin:0;font-size:13px;color:#52525b;line-height:1.5;">'
        "Приглашение действительно 7 дней.</p>"
    )
    html = _brand_html("Приглашение в команду", body)
    asyncio.create_task(
        _send_email_async(email, f"Приглашение в {company_name} — CallForce", html)
    )


def send_payment_confirmation_email(email: str, plan_name: str, amount: str) -> None:
    body = (
        '<p style="margin:0 0 16px;font-size:15px;color:#a1a1aa;line-height:1.6;">'
        f"Оплата подписки <strong style='color:#10b981;'>{plan_name}</strong> "
        f"на сумму <strong style='color:#ffffff;'>{amount} ₽</strong> "
        f"успешно произведена через ЮKassa.</p>"
        '<div style="margin:20px 0;padding:16px;background:#09090b;border-radius:10px;border:1px solid rgba(255,255,255,0.05);">'
        f'<div style="font-size:13px;color:#71717a;">Тарифный план</div>'
        f'<div style="font-size:18px;font-weight:700;color:#10b981;margin-top:4px;">{plan_name}</div>'
        "</div>"
        '<p style="margin:0;font-size:13px;color:#52525b;">'
        "Квитанция об оплате доступна в разделе Биллинг вашего личного кабинета.</p>"
    )
    html = _brand_html("Оплата подтверждена ✓", body)
    asyncio.create_task(
        _send_email_async(email, f"Оплата подтверждена — CallForce {plan_name}", html)
    )
