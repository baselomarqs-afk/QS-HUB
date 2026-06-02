"""Auth-adjacent production helpers for Streamlit."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta

import bcrypt

from utils.db import safe_execute, safe_query


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def password_ok(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def issue_reset_token(email: str) -> str | None:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    success, _ = safe_execute(
        """
        UPDATE qto_users
        SET reset_token_hash=%s, reset_token_expires_at=%s
        WHERE email=%s
        """,
        (hash_token(token), expires.strftime("%Y-%m-%d %H:%M:%S"), email),
    )
    df = safe_query("SELECT id FROM qto_users WHERE email=%s", (email,))
    return token if success and not df.empty else None


def reset_password(token: str, new_password: str) -> bool:
    token_h = hash_token(token)
    df = safe_query(
        """
        SELECT id FROM qto_users
        WHERE reset_token_hash=%s AND reset_token_expires_at > UTC_TIMESTAMP()
        LIMIT 1
        """,
        (token_h,),
    )
    if df.empty:
        return False
    user_id = int(df.iloc[0]["id"])
    ok, _ = safe_execute(
        """
        UPDATE qto_users
        SET password_hash=%s, reset_token_hash=NULL, reset_token_expires_at=NULL
        WHERE id=%s
        """,
        (password_hash(new_password), user_id),
    )
    return bool(ok)


def login_rate_limited(email: str, max_attempts: int = 8) -> bool:
    df = safe_query(
        """
        SELECT metadata
        FROM qto_usage_logs
        WHERE event_type='login_failed'
          AND created_at > DATE_SUB(NOW(), INTERVAL 15 MINUTE)
        """,
    )
    if df.empty:
        return False
    attempts = 0
    target = (email or "").strip().lower()
    for row in df.to_dict("records"):
        try:
            metadata = row.get("metadata") or "{}"
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            logged_email = str(metadata.get("email", "")).strip().lower()
            if logged_email == target:
                attempts += 1
        except Exception:
            continue
    return attempts >= max_attempts


def touch_login(user_id: int) -> None:
    safe_execute("UPDATE qto_users SET last_login_at=NOW() WHERE id=%s", (user_id,))
