"""AI Agents API — Senior UAE QS Engineer (`role='qs'`) & Customer Support (`role='cc'`)."""
import asyncio
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import get_current_user
from utils.db import safe_query, safe_execute
from utils.usage import EVENT_AI_CALL, check_limit, log_usage
from utils.agents_logic import generate_agent_response

router = APIRouter()

# Lightweight anti-spam rate limiter for Customer Support (exempt from paid AI_CALL paywall
# so unsubscribed or quota-reached users can ALWAYS ask Customer Support for help!)
_SUPPORT_RATE: dict[int, list[float]] = defaultdict(list)


def _check_support_spam(user_id: int, max_per_hour: int = 40) -> None:
    now = time.time()
    recent = [ts for ts in _SUPPORT_RATE[user_id] if now - ts < 3600]
    if len(recent) >= max_per_hour:
        raise HTTPException(status_code=429, detail="Too many support messages in the last hour. Please wait a moment.")
    recent.append(now)
    _SUPPORT_RATE[user_id] = recent


class ChatRequest(BaseModel):
    prompt: str
    role: str = "cc"  # "cc" for Customer Support, "qs" for Senior QS Engineer


@router.post("/chat")
async def chat_with_agent(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    role = current_user["role"]
    agent_role = req.role.strip().lower()

    if agent_role == "mgr" and role != "admin":
        raise HTTPException(status_code=403, detail="The AI Manager is only accessible to system administrators.")

    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    if agent_role == "cc":
        # Customer Support is ALWAYS accessible (even with 0 paid credits), with anti-spam protection
        _check_support_spam(user_id)
    else:
        # QS Assistant checks subscription AI limit (admins & users with free/active quota pass)
        if role != "admin":
            ok, msg = check_limit(current_user, EVENT_AI_CALL)
            # Also allow users who hold an active programme/cashflow plan or unused free trial
            if not ok:
                from utils.usage import project_entitlement
                has_any = any(project_entitlement(current_user, f)["can_create"] for f in ("qto", "programme", "cashflow"))
                if not has_any:
                    raise HTTPException(status_code=429, detail=msg)
        log_usage(user_id, EVENT_AI_CALL, metadata={"role": agent_role})

    is_ar = any("\u0600" <= c <= "\u06FF" for c in req.prompt)
    reply = await asyncio.to_thread(generate_agent_response, req.prompt.strip(), agent_role, is_ar, user_id)

    return {"reply": reply, "role": agent_role}


@router.get("/history")
async def get_chat_history(
    role: str = Query("cc"),
    current_user: dict = Depends(get_current_user),
):
    if role == "mgr" and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="The AI Manager history is only accessible to system administrators.")

    df = safe_query(
        "SELECT sender, message, created_at FROM qto_agent_conversations WHERE user_id=%s AND agent_role=%s ORDER BY id ASC",
        (current_user["id"], role),
    )
    if df.empty:
        return []
    return df.to_dict("records")


@router.delete("/history")
async def clear_chat_history(
    role: str = Query("qs"),
    current_user: dict = Depends(get_current_user),
):
    if role == "mgr" and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    safe_execute(
        "DELETE FROM qto_agent_conversations WHERE user_id=%s AND agent_role=%s",
        (current_user["id"], role),
    )
    return {"ok": True}
