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
