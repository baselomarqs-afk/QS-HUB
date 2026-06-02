from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json

from api.auth import get_current_user
from utils.db import safe_query, safe_execute

router = APIRouter()

class UpdateRuleReq(BaseModel):
    rule_id: int

class ResolveComplaintReq(BaseModel):
    complaint_id: int

class AdminChatReq(BaseModel):
    prompt: str

def verify_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Administrators only.")
    return current_user

@router.get("/users")
async def get_users(admin: dict = Depends(verify_admin)):
    df = safe_query("SELECT id, email, role, created_at FROM qto_users ORDER BY id DESC")
    if df.empty:
        return []
    return df.to_dict("records")

@router.get("/subscriptions")
async def get_subscriptions(admin: dict = Depends(verify_admin)):
    df = safe_query(
        """
        SELECT s.id, s.user_id, u.email as user_email, s.plan_tier, s.provider, s.status, 
               s.current_period_end, s.projects_used, s.ai_calls_used, s.exports_used, s.created_at
        FROM qto_subscriptions s
        JOIN qto_users u ON s.user_id = u.id
        ORDER BY s.id DESC
        LIMIT 200
        """
    )
    if df.empty:
        return []
    return df.to_dict("records")

@router.get("/stats")
async def get_system_stats(admin: dict = Depends(verify_admin)):
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Database connection check
    db_ok = False
    db_err = None
    try:
        from utils.db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_ok = True
    except Exception as e:
        db_err = str(e)

    # 2. Environment variables check
    required_env = ["TIDB_HOST", "TIDB_USER", "TIDB_PASSWORD", "TIDB_DATABASE"]
    env_status = {}
    for env in required_env:
        env_status[env] = bool(os.environ.get(env))

    # 3. Cache directory check
    cache_dir = os.path.join(ROOT, ".qto_cache")
    cache_exists = os.path.exists(cache_dir)
    cache_count = 0
    cache_size_mb = 0.0
    if cache_exists:
        files = [f for f in os.listdir(cache_dir) if f.endswith(".json")]
        cache_count = len(files)
        for f in os.listdir(cache_dir):
            fp = os.path.join(cache_dir, f)
            if os.path.isfile(fp):
                try:
                    cache_size_mb += os.path.getsize(fp) / (1024 * 1024)
                except:
                    pass

    # 4. OCR Ready Check
    ocr_ok = False
    try:
        import easyocr
        ocr_ok = True
    except:
        pass

    # 5. PyMuPDF Blueprint Engine Check
    pdf_ok = False
    try:
        import fitz
        pdf_ok = True
    except:
        pass

    return {
        "db_ok": db_ok,
        "db_error": db_err,
        "env_status": env_status,
        "cache": {
            "exists": cache_exists,
            "count": cache_count,
            "size_mb": round(cache_size_mb, 2)
        },
        "ocr_ready": ocr_ok,
        "pdf_ready": pdf_ok,
        "system_perfect": db_ok and all(env_status.values()) and ocr_ok and pdf_ok
    }

@router.get("/memory-rules")
async def get_memory_rules(admin: dict = Depends(verify_admin)):
    # Fetch pending rules
    pending_df = safe_query(
        "SELECT id, user_id, original_text, mapped_category, status, created_at FROM qto_memory_rules WHERE status='pending' ORDER BY id ASC"
    )
    pending = [] if pending_df.empty else pending_df.to_dict("records")
    
    # Fetch global rules
    global_df = safe_query(
        "SELECT id, original_text, mapped_category, created_at FROM qto_memory_rules WHERE status='global' ORDER BY id DESC"
    )
    global_rules = [] if global_df.empty else global_df.to_dict("records")
    
    return {
        "pending": pending,
        "global": global_rules
    }

@router.post("/memory-rules/approve")
async def approve_memory_rule(req: UpdateRuleReq, admin: dict = Depends(verify_admin)):
    df = safe_query("SELECT user_id, original_text FROM qto_memory_rules WHERE id=%s", (req.rule_id,))
    if df.empty:
        raise HTTPException(status_code=404, detail="Rule not found.")
        
    user_id = df.iloc[0]["user_id"]
    original_text = df.iloc[0]["original_text"]
    
    # Upgrade rule to global
    safe_execute("UPDATE qto_memory_rules SET status='global', user_id=NULL WHERE id=%s", (req.rule_id,))
    
    # Delete personal rule if it overlaps
    if user_id:
        safe_execute("DELETE FROM qto_memory_rules WHERE status='personal' AND user_id=%s AND original_text=%s", (user_id, original_text))
        
    return {"success": True, "message": "Rule approved globally."}

@router.post("/memory-rules/reject")
async def reject_memory_rule(req: UpdateRuleReq, admin: dict = Depends(verify_admin)):
    safe_execute("DELETE FROM qto_memory_rules WHERE id=%s", (req.rule_id,))
    return {"success": True, "message": "Rule rejected and removed."}

@router.get("/complaints")
async def get_complaints(admin: dict = Depends(verify_admin)):
    df = safe_query(
        """
        SELECT c.id, c.user_id, u.email as user_email, c.complaint_text, c.status, c.created_at 
        FROM qto_customer_complaints c
        JOIN qto_users u ON c.user_id = u.id
        ORDER BY c.id DESC
        """
    )
    if df.empty:
        return []
    return df.to_dict("records")

@router.post("/complaints/resolve")
async def resolve_complaint(req: ResolveComplaintReq, admin: dict = Depends(verify_admin)):
    safe_execute("UPDATE qto_customer_complaints SET status='resolved' WHERE id=%s", (req.complaint_id,))
    return {"success": True, "message": "Complaint marked as resolved."}

@router.post("/chat")
async def chat_with_manager(req: AdminChatReq, admin: dict = Depends(verify_admin)):
    # AI Manager chat interface
    from utils.admin_agent import process_admin_message
    
    # Fetch admin name
    admin_name = admin.get("email", "Admin").split("@")[0]
    admin_id = admin.get("id", 1)
    
    # Simply pass empty history or query log for previous chats
    df_history = safe_query(
        "SELECT sender, message FROM qto_agent_conversations WHERE user_id=%s AND agent_role='mgr' ORDER BY id DESC LIMIT 10",
        (admin_id,)
    )
    history = []
    if not df_history.empty:
        # Re-arrange back to ASC order for context
        df_history = df_history.iloc[::-1]
        for idx, row in df_history.iterrows():
            role_map = "user" if row["sender"] == "user" else "assistant"
            history.append({"role": role_map, "content": row["message"]})
            
    # Add new user message to local history for process_admin_message context
    history_ctx = list(history)
    
    reply, action_result = process_admin_message(
        req.prompt,
        history_ctx,
        admin_name,
        admin_id
    )
    
    # Log conversation in database
    safe_execute(
        "INSERT INTO qto_agent_conversations (user_id, agent_role, sender, message) VALUES (%s, %s, %s, %s)",
        (admin_id, "mgr", "user", req.prompt)
    )
    safe_execute(
        "INSERT INTO qto_agent_conversations (user_id, agent_role, sender, message) VALUES (%s, %s, %s, %s)",
        (admin_id, "mgr", "system" if action_result else "assistant", reply)
    )
    
    return {
        "reply": reply,
        "action_result": action_result
    }
