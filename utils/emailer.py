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

def send_project_followup_email(to_email: str) -> bool:
    subject = "كيف كانت تجربتك؟ | How was your experience with THE QS HUB? 🎁"
    body = f"""مرحباً،
يسعدنا أنك أنهيت مشروعك المجاني بنجاح! 
نتمنى أن يكون الذكاء الاصطناعي قد وفر عليك الوقت في استخراج الكميات. رأيك يهمنا جداً لتطوير المنصة، ما هو تقييمك للتجربة؟

🎁 هدية ترحيبية: يمكنك الآن الحصول على خصم 50% على اشتراكاتنا الشهرية باستخدام الكود: QTO2026.
إذا كان لديك مشروع واحد إضافي، يمكنك الآن شراءه بـ 50 درهم فقط (Pay-as-you-go).

لترقية حسابك: {app_base_url()}
-----------------------------
Hi,
We noticed you successfully completed your free project! 
We hope our AI saved you valuable time. Your feedback means everything to us, how was your experience?

🎁 Welcome Gift: Enjoy 50% OFF our monthly plans with code: QTO2026.
Or, if you just have one upcoming project, you can now buy a single project allowance for 50 AED (Pay-as-you-go).

To upgrade your account: {app_base_url()}

THE QS HUB Team
"""
    return send_email(to_email, subject, body)
