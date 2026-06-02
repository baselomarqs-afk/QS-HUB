"""SMTP email delivery for account lifecycle emails."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from utils.settings import app_base_url, get_int_setting, get_setting


def smtp_configured() -> bool:
    return bool(get_setting("SMTP_HOST") and get_setting("SMTP_FROM"))


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not smtp_configured():
        return False
    msg = EmailMessage()
    msg["From"] = get_setting("SMTP_FROM")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    host = get_setting("SMTP_HOST", required=True)
    port = get_int_setting("SMTP_PORT", 587)
    username = get_setting("SMTP_USER")
    password = get_setting("SMTP_PASSWORD")

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(msg)
    return True


def send_password_reset(to_email: str, token: str) -> bool:
    reset_url = f"{app_base_url()}/?reset_token={token}"
    return send_email(
        to_email,
        "Reset your THE QS HUB password",
        f"Use this secure link to reset your password:\n\n{reset_url}\n\nThis link expires in 1 hour.",
    )
