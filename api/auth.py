from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr
import hmac
import hashlib
import time
import os
from typing import Optional
from utils.db import safe_query, safe_execute
from utils.security import password_hash, password_ok, login_rate_limited, touch_login

router = APIRouter()

# Session-signing secret. MUST come from env in production — no hardcoded fallback
# (a known constant would let anyone forge valid session tokens).
SECRET_KEY = os.environ.get("JWT_SECRET") or os.environ.get("AI_API_KEY")

if not SECRET_KEY:
    SECRET_KEY = "fallback_secret_for_now_123_qto_hub"
    # Dev only: ephemeral random secret (all sessions invalidate on restart).
    import secrets as _secrets
    SECRET_KEY = _secrets.token_hex(32)

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ResetPasswordReq(BaseModel):
    email: EmailStr

class UpdatePasswordReq(BaseModel):
    token: str
    password: str

def generate_session_token(user_id: int, role: str, token_version: int = 0) -> str:
    expiry = int(time.time()) + 8 * 3600  # 8 hours session
    msg = f"{user_id}:{role}:{token_version}:{expiry}"
    sig = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}:{sig}"

def verify_session_token(token: str) -> dict:
    try:
        parts = token.split(":")
        if len(parts) != 5:
            raise HTTPException(status_code=401, detail="Invalid session token format")
        user_id, role, token_version, expiry, sig = parts
        msg = f"{user_id}:{role}:{token_version}:{expiry}"
        expected_sig = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise HTTPException(status_code=401, detail="Session signature mismatch")
        if int(expiry) < time.time():
            raise HTTPException(status_code=401, detail="Session expired")
        # Check token_version against DB to allow instant revocation
        df = safe_query("SELECT email, COALESCE(token_version, 0) as tv FROM qto_users WHERE id=%s", (user_id,))
        if df.empty:
            raise HTTPException(status_code=401, detail="User not found")
        db_version = int(df.iloc[0]["tv"])
        if int(token_version) != db_version:
            raise HTTPException(status_code=401, detail="Session revoked — please log in again")
        email = df.iloc[0]["email"]
        return {"id": int(user_id), "role": role, "email": email}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(request: Request, authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        authorization = request.query_params.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    return verify_session_token(token)

@router.post("/register")
async def register(req: UserRegister):
    email = req.email.strip().lower()
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    
    # Check if user already exists
    df = safe_query("SELECT id FROM qto_users WHERE email=%s", (email,))
    if not df.empty:
        raise HTTPException(status_code=400, detail="User with this email already exists.")
    
    hashed = password_hash(req.password)
    success, err = safe_execute(
        "INSERT INTO qto_users (email, password_hash, role) VALUES (%s, %s, %s)",
        (email, hashed, "user")
    )
    if not success:
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {err}")
    
    return {"message": "User registered successfully."}

@router.post("/login")
async def login(req: UserLogin):
    email = req.email.strip().lower()
    
    if login_rate_limited(email):
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Please try again in 15 minutes.")
        
    df = safe_query("SELECT id, email, password_hash, role FROM qto_users WHERE email=%s", (email,))
    if df.empty:
        # Log failed attempt
        safe_execute(
            "INSERT INTO qto_usage_logs (event_type, metadata) VALUES (%s, %s)",
            ("login_failed", f'{{"email": "{email}"}}')
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    user = df.iloc[0]
    if not password_ok(req.password, user["password_hash"]):
        safe_execute(
            "INSERT INTO qto_usage_logs (event_type, metadata) VALUES (%s, %s)",
            ("login_failed", f'{{"email": "{email}"}}')
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    if user["role"] == "blocked":
        raise HTTPException(status_code=403, detail="Your account has been suspended.")
        
    touch_login(user["id"])
    # Read token_version for revocation support
    tv_df = safe_query("SELECT COALESCE(token_version, 0) as tv FROM qto_users WHERE id=%s", (user["id"],))
    tv = int(tv_df.iloc[0]["tv"]) if not tv_df.empty else 0
    token = generate_session_token(user["id"], user["role"], tv)
    
    return {
        "token": token,
        "user": {
            "id": int(user["id"]),
            "email": user["email"],
            "role": user["role"]
        }
    }

@router.get("/profile")
async def profile(current_user: dict = Depends(get_current_user)):
    df = safe_query("SELECT id, email, role, created_at FROM qto_users WHERE id=%s", (current_user["id"],))
    if df.empty:
        raise HTTPException(status_code=404, detail="User not found")
    user = df.iloc[0]
    
    # Get plan information
    from utils.plans import get_plan_for_user
    plan = get_plan_for_user(user["id"], user["role"])
    
    return {
        "id": int(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
        "plan": {
            "tier": plan.tier,
            "name": plan.name,
            "project_limit": plan.projects,
            "ai_call_limit": plan.ai_calls,
            "export_limit": plan.exports
        }
    }

@router.post("/forgot-password")
async def forgot_password(req: ResetPasswordReq):
    from utils.security import issue_reset_token
    token = issue_reset_token(req.email)
    if token:
        import logging
        logging.getLogger("qto").info("Password reset token for %s: %s", req.email, token)
        # Send actual email
        from utils.mailer import send_reset_email
        send_reset_email(req.email, token)
    # Always return the same generic message — do not reveal whether the email exists
    # (prevents account enumeration).
    return {"message": "If an account exists for this email, a reset token has been sent."}

@router.post("/reset-password")
async def reset_password_route(req: UpdatePasswordReq):
    from utils.security import reset_password
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if reset_password(req.token, req.password):
        return {"message": "Password updated successfully."}
    raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
