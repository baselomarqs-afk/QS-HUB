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

class UpdateInquiryStatusReq(BaseModel):
    inquiry_id: int
    status: str

class ToggleReviewApproveReq(BaseModel):
    review_id: int
    is_approved: Optional[int] = None

class ToggleReviewFeatureReq(BaseModel):
    review_id: int
    is_featured: Optional[int] = None

class DeleteReviewReq(BaseModel):
    review_id: int

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
        SELECT s.id, s.user_id, u.email as user_email, s.feature, s.plan_tier, s.provider, s.status,
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

    # 6. User and Project Analytics
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    t_12h = (now - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    today = now.strftime('%Y-%m-%d')

    # Visitor Analytics
    from utils.visitor import get_visitor_stats
    v_stats = get_visitor_stats()

    logins_today = 0
    regs_today = 0
    projects_12h = 0
    recent_projects = []

    try:
        df_logins = safe_query(f"SELECT id FROM qto_users WHERE DATE(last_login_at) = '{today}'")
        logins_today = len(df_logins) if not df_logins.empty else 0

        df_regs = safe_query(f"SELECT id FROM qto_users WHERE DATE(created_at) = '{today}'")
        regs_today = len(df_regs) if not df_regs.empty else 0

        df_projs = safe_query(f"SELECT id FROM qto_projects WHERE created_at >= '{t_12h}'")
        projects_12h = len(df_projs) if not df_projs.empty else 0

        df_recent = safe_query(
            """
            SELECT p.id, p.name, p.status, p.current_step, p.created_at, u.email as user_email
            FROM qto_projects p
            JOIN qto_users u ON p.user_id = u.id
            ORDER BY p.id DESC
            LIMIT 15
            """
        )
        if not df_recent.empty:
            recent_projects = df_recent.to_dict("records")
    except Exception as e:
        print(f"Error fetching analytics: {e}")

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
        "system_perfect": db_ok and all(env_status.values()) and ocr_ok and pdf_ok,
        "analytics": {
            "logins_today": logins_today,
            "regs_today": regs_today,
            "projects_12h": projects_12h,
            "visitors_24h": v_stats["visitors_24h"],
            "unique_visitors_24h": v_stats["unique_visitors_24h"],
            "visitors_today": v_stats["visitors_today"],
            "recent_projects": recent_projects
        }
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

@router.get("/inquiries")
async def get_inquiries(admin: dict = Depends(verify_admin)):
    df = safe_query(
        """
        SELECT id, user_id, name, email, subject, message, category, status, admin_notes, created_at
        FROM qto_inquiries
        ORDER BY id DESC
        """
    )
    if df.empty:
        return []
    return df.to_dict("records")

@router.post("/inquiries/status")
async def update_inquiry_status(req: UpdateInquiryStatusReq, admin: dict = Depends(verify_admin)):
    status = req.status.lower().strip()
    if status not in ["new", "in_progress", "resolved"]:
        status = "resolved"
    safe_execute("UPDATE qto_inquiries SET status=%s WHERE id=%s", (status, req.inquiry_id))
    return {"success": True, "message": f"Inquiry status updated to {status}."}

@router.get("/reviews")
async def get_all_reviews(admin: dict = Depends(verify_admin)):
    # Ensure mockup reviews are populated if empty
    try:
        from utils.db import seed_mockup_reviews
        seed_mockup_reviews()
    except Exception:
        pass
    df = safe_query(
        """
        SELECT id, user_id, user_name, user_role, company, rating, review_title, review_text, is_approved, is_featured, created_at
        FROM qto_reviews
        ORDER BY id DESC
        """
    )
    if df.empty:
        return []
    return df.to_dict("records")

@router.post("/reviews/toggle-approve")
async def toggle_review_approve(req: ToggleReviewApproveReq, admin: dict = Depends(verify_admin)):
    if req.is_approved is not None:
        new_val = 1 if req.is_approved else 0
    else:
        # Toggle current
        df = safe_query("SELECT is_approved FROM qto_reviews WHERE id=%s", (req.review_id,))
        if df.empty:
            raise HTTPException(status_code=404, detail="Review not found")
        curr = int(df.iloc[0]["is_approved"] or 0)
        new_val = 0 if curr == 1 else 1
        
    safe_execute("UPDATE qto_reviews SET is_approved=%s WHERE id=%s", (new_val, req.review_id))
    return {"success": True, "is_approved": new_val, "message": "Review approval status updated."}

@router.post("/reviews/toggle-feature")
async def toggle_review_feature(req: ToggleReviewFeatureReq, admin: dict = Depends(verify_admin)):
    if req.is_featured is not None:
        new_val = 1 if req.is_featured else 0
    else:
        df = safe_query("SELECT is_featured FROM qto_reviews WHERE id=%s", (req.review_id,))
        if df.empty:
            raise HTTPException(status_code=404, detail="Review not found")
        curr = int(df.iloc[0]["is_featured"] or 0)
        new_val = 0 if curr == 1 else 1
        
    safe_execute("UPDATE qto_reviews SET is_featured=%s WHERE id=%s", (new_val, req.review_id))
    return {"success": True, "is_featured": new_val, "message": "Review featured status updated."}

@router.post("/reviews/delete")
async def delete_review(req: DeleteReviewReq, admin: dict = Depends(verify_admin)):
    safe_execute("DELETE FROM qto_reviews WHERE id=%s", (req.review_id,))
    return {"success": True, "message": "Review deleted successfully."}

@router.get("/feedback")

async def get_feedback(admin: dict = Depends(verify_admin)):
    # Per-tool summary (count + average rating), so the admin sees how each tool
    # is rated at a glance, plus the full list of individual ratings/reasons.
    summary_df = safe_query(
        """
        SELECT tool_name,
               COUNT(*) AS total,
               AVG(rating) AS avg_rating,
               SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) AS positive,
               SUM(CASE WHEN rating <= 3 THEN 1 ELSE 0 END) AS negative
        FROM qto_project_feedback
        GROUP BY tool_name
        ORDER BY total DESC
        """
    )
    items_df = safe_query(
        """
        SELECT f.id, f.user_id, u.email AS user_email, f.tool_name, f.project_name,
               f.rating, f.reason, f.created_at
        FROM qto_project_feedback f
        LEFT JOIN qto_users u ON f.user_id = u.id
        ORDER BY f.id DESC
        """
    )
    summary = summary_df.to_dict("records") if not summary_df.empty else []
    for s in summary:
        # Round the average for clean display.
        try:
            s["avg_rating"] = round(float(s["avg_rating"]), 2)
        except (TypeError, ValueError):
            s["avg_rating"] = 0
    return {
        "summary": summary,
        "items": items_df.to_dict("records") if not items_df.empty else [],
    }

@router.post("/chat")
def chat_with_manager(req: AdminChatReq, admin: dict = Depends(verify_admin)):
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
