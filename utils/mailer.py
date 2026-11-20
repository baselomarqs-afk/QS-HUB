import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_admin_email(subject: str, body_html: str) -> bool:
    """
    Sends a real email via SMTP to the Admin.
    Expects SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, QTO_ADMIN_EMAIL in environment variables.
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    # SECURITY: no hardcoded SMTP credentials. Provide via env (rotate any that leaked).
    smtp_pass = os.environ.get("SMTP_PASS") or os.environ.get("SMTP_PASSWORD") or ""
    admin_email = os.environ.get("QTO_ADMIN_EMAIL", "")
    from_email = os.environ.get("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass:
        print("SMTP credentials not configured. Email not sent.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"AI Manager <{from_email}>"
    msg["To"] = admin_email

    part1 = MIMEText(body_html, "html")
    msg.attach(part1)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, admin_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_reset_email(to_email: str, token: str) -> bool:
    """
    Sends a password reset email to the user.
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS") or os.environ.get("SMTP_PASSWORD") or ""
    from_email = os.environ.get("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass:
        print("SMTP credentials not configured. Email not sent.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Password Reset Token - THE QS HUB"
    msg["From"] = f"The QS Hub <{from_email}>"
    msg["To"] = to_email

    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
        <h2 style="color: #3b82f6;">Password Reset</h2>
        <p>You requested a password reset for your THE QS HUB account.</p>
        <p>Please use the following reset token on the platform to set a new password:</p>
        <div style="background-color: #f3f4f6; padding: 15px; text-align: center; font-size: 20px; font-weight: bold; letter-spacing: 2px; border-radius: 8px; margin: 20px 0;">
            {token}
        </div>
        <p style="color: #666; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
    </div>
    """
    part1 = MIMEText(body_html, "html")
    msg.attach(part1)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send reset email: {e}")
        return False
def send_custom_email(subject: str, body_html: str, to_email: str) -> bool:
    """
    Sends a custom email via SMTP to a specific user.
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS") or os.environ.get("SMTP_PASSWORD") or ""
    from_email = os.environ.get("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass:
        print("SMTP credentials not configured. Email not sent.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"The QS Hub <{from_email}>"
    msg["To"] = to_email

    part1 = MIMEText(body_html, "html")
    msg.attach(part1)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send custom email: {e}")
        return False


def send_verification_email(to_email: str, code: str, name: str | None = None) -> bool:
    """Send a bilingual 6-digit email verification code to newly registered users."""
    import html as _html
    safe_name = _html.escape((name or "").strip())
    greeting_en = f"Hi {safe_name}," if safe_name else "Hi,"
    greeting_ar = f"مرحباً {safe_name}،" if safe_name else "مرحباً،"
    safe_code = _html.escape(str(code))
    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px;">
        <h2 style="color: #2563eb; margin-top: 0;">THE QS HUB — Verify Your Email | تأكيد البريد الإلكتروني</h2>
        <p>{greeting_en}</p>
        <p>Welcome to <strong>THE QS HUB</strong>! Enter this 6-digit verification code to activate your account and unlock your free trial project in each tool:</p>
        <div style="background: #f1f5f9; border: 2px dashed #3b82f6; padding: 18px; text-align: center; font-size: 30px; font-weight: 800; letter-spacing: 8px; color: #0f172a; border-radius: 10px; margin: 20px 0;">
            {safe_code}
        </div>
        <p style="color: #64748b; font-size: 13px;">This code expires in 30 minutes.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;"/>
        <div dir="rtl" style="text-align: right;">
            <p>{greeting_ar}</p>
            <p>أهلاً بك في منصة <strong>THE QS HUB</strong>! يرجى إدخال رمز التأكيد المكوّن من 6 أرقام أعلاه لتفعيل حسابك والبدء فوراً في مشروعك المجاني.</p>
            <p style="color: #64748b; font-size: 13px;">صلاحية الرمز 30 دقيقة. إذا لم تقم بالتسجيل يمكنك تجاهل هذه الرسالة.</p>
        </div>
    </div>
    """
    return send_custom_email("THE QS HUB — Email Verification Code | رمز تأكيد الحساب", body_html, to_email)
