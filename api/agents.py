from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from api.auth import get_current_user
from utils.db import safe_query
from utils.usage import EVENT_AI_CALL, check_limit, log_usage
from utils.agents_logic import generate_agent_response, log_agent_conversation

router = APIRouter()

class ChatRequest(BaseModel):
    prompt: str
    role: str = "cc" # "cc" for customer care Sarah, "qs" for Quantity Surveyor

@router.post("/chat")
async def chat_with_agent(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    email = current_user["email"]
    role = current_user["role"]
    
    # Check role restriction for AI Manager
    if req.role == "mgr" and role != "admin":
        raise HTTPException(status_code=403, detail="The AI Manager is only accessible to system administrators.")

    # Check limit for AI calls
    # Note: In check_limit, it checks subscription limits
    ok, msg = check_limit(current_user, EVENT_AI_CALL)
    if not ok:
        raise HTTPException(status_code=429, detail=msg)
        
    # Log usage
    log_usage(user_id, EVENT_AI_CALL, metadata={"role": req.role})
    
    # Check if Arabic is requested (ar=True)
    # We can detect Arabic characters in the prompt, or default to Arabic since user requested Arabic answers!
    # Let's check prompt language
    is_ar = any(u"\u0600" <= c <= u"\u06FF" for c in req.prompt)
    
    # Call underlying response engine
    reply = generate_agent_response(req.prompt, req.role, is_ar, user_id)
    
    return {
        "reply": reply,
        "role": req.role
    }

@router.get("/history")
async def get_chat_history(
    role: str = Query("cc"),
    current_user: dict = Depends(get_current_user)
):
    if role == "mgr" and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="The AI Manager history is only accessible to system administrators.")

    df = safe_query(
        "SELECT sender, message, created_at FROM qto_agent_conversations WHERE user_id=%s AND agent_role=%s ORDER BY id ASC",
        (current_user["id"], role)
    )
    if df.empty:
        return []
        
    return df.to_dict("records")
