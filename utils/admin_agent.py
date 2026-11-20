"""AI Operations Director & Platform Supervisor for THE QS HUB.

Real, production-grade administrative agent with 20+ verified working tools
covering Executive KPIs & real MRR revenue, per-tool user/subscription/credit
management across QTO / Work Programme / Cash Flow, Customer Support & Inquiry
supervision, Review & AI Learning moderation, live Google-Search Market Price
syncing, real SMTP emails, Dodo refunds, and live system + 20-key pool health.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from utils.audit import audit_log
from utils.db import get_connection, is_sqlite, safe_execute, safe_query
from utils.features import FEATURE_EXTRA_COL, extra_projects_for
from utils.key_manager import get_key_manager
from utils.plans import PLANS, get_active_subscription, get_plan_for_user
from utils.usage import EVENT_PROJECT, monthly_usage, project_entitlement

DANGEROUS_ACTIONS = {
    "delete_user",
    "delete_project",
    "block_user",
    "update_user_role",
    "grant_subscription",
    "grant_extra_credits",
    "cancel_subscription",
    "run_safe_maintenance",
    "send_user_email",
    "issue_refund",
}

VALID_FEATURES = ("qto", "programme", "cashflow")


def _resolve_user(action: dict) -> Optional[dict]:
    """Find a user by userId or email."""
    uid = action.get("userId")
    email = (action.get("email") or "").strip()
    if uid is not None:
        df = safe_query("SELECT id, email, role, created_at FROM qto_users WHERE id=%s", (int(uid),))
        if not df.empty:
            return df.iloc[0].to_dict()
    if email:
        df = safe_query("SELECT id, email, role, created_at FROM qto_users WHERE LOWER(email)=LOWER(%s) LIMIT 1", (email,))
        if not df.empty:
            return df.iloc[0].to_dict()
    return None


def _clear_plan_caches() -> None:
    try:
        get_active_subscription.clear()
        get_plan_for_user.clear()
        monthly_usage.clear()
    except Exception:
        pass


def _build_executive_dashboard() -> dict:
    """Compute REAL live executive metrics and REAL MRR revenue from active subscriptions."""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    d7_str = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    def _count(sql: str, params: tuple = ()) -> int:
        df = safe_query(sql, params)
        if df.empty:
            return 0
        try:
            return int(df.iloc[0]["c"] or 0)
        except Exception:
            return 0

    total_users = _count("SELECT COUNT(*) AS c FROM qto_users")
    regs_today = _count("SELECT COUNT(*) AS c FROM qto_users WHERE DATE(created_at) = %s", (today_str,))
    regs_7d = _count("SELECT COUNT(*) AS c FROM qto_users WHERE created_at >= %s", (d7_str,))

    # REAL MRR calculated from exact PLANS[tier].monthly_price_aed per active subscription & tool
    sub_df = safe_query("SELECT feature, plan_tier, status FROM qto_subscriptions WHERE status IN ('active', 'trialing')")
    mrr_total = 0
    subs_by_tool: Dict[str, int] = {"qto": 0, "programme": 0, "cashflow": 0}
    mrr_by_tool: Dict[str, int] = {"qto": 0, "programme": 0, "cashflow": 0}
    subs_by_tier: Dict[str, int] = {}
    if not sub_df.empty:
        for _, row in sub_df.iterrows():
            feat = str(row.get("feature") or "qto").lower()
            tier = int(row.get("plan_tier") or 0)
            price = PLANS.get(tier, PLANS[0]).monthly_price_aed
            mrr_total += price
            if feat in subs_by_tool:
                subs_by_tool[feat] += 1
                mrr_by_tool[feat] += price
            t_name = f"Tier {tier} ({PLANS.get(tier, PLANS[0]).name})"
            subs_by_tier[t_name] = subs_by_tier.get(t_name, 0) + 1

    qto_projects = _count("SELECT COUNT(*) AS c FROM qto_projects")
    prog_projects = _count("SELECT COUNT(*) AS c FROM qto_module_projects WHERE feature='programme'")
    cf_projects = _count("SELECT COUNT(*) AS c FROM qto_module_projects WHERE feature='cashflow'")
    open_complaints = _count("SELECT COUNT(*) AS c FROM qto_customer_complaints WHERE status='open'")
    new_inquiries = _count("SELECT COUNT(*) AS c FROM qto_inquiries WHERE status='new'")
    pending_rules = _count("SELECT COUNT(*) AS c FROM qto_memory_rules WHERE status='pending'")

    # Per-tool average feedback rating
    fb_df = safe_query("SELECT tool_name, COUNT(*) AS cnt, AVG(rating) AS avg_r FROM qto_project_feedback GROUP BY tool_name")
    feedback_summary = {}
    if not fb_df.empty:
        for _, r in fb_df.iterrows():
            feedback_summary[str(r["tool_name"])] = f"{round(float(r['avg_r'] or 0), 2)}/5 ({int(r['cnt'] or 0)} ratings)"

    from utils.visitor import get_visitor_stats
    v_stats = get_visitor_stats()

    return {
        "Generated At": now.strftime("%Y-%m-%d %H:%M"),
        "Users": {"Total": total_users, "New Today": regs_today, "New Last 7d": regs_7d},
        "Active Subscriptions": sum(subs_by_tool.values()),
        "Subscriptions By Tool": subs_by_tool,
        "Subscriptions By Tier": subs_by_tier,
        "Real Monthly Recurring Revenue (MRR)": f"{mrr_total:,} AED",
        "Revenue By Tool (AED)": mrr_by_tool,
        "Projects Created (All Time)": {"QTO": qto_projects, "Work Programme": prog_projects, "Cash Flow": cf_projects},
        "Support & Operations Queue": {
            "Open Customer Support Tickets": open_complaints,
            "New Inquiries": new_inquiries,
            "Pending AI Learning Rules": pending_rules,
        },
        "Tool Feedback Ratings": feedback_summary or "No ratings yet",
        "Live Visitor Traffic (24h)": {
            "Page Views": v_stats.get("visitors_24h", 0),
            "Unique IPs": v_stats.get("unique_visitors_24h", 0),
            "Today": v_stats.get("visitors_today", 0),
        },
    }


def execute_admin_action(admin_id: int, action: dict) -> dict:
    """Execute verified real administrative operations on THE QS HUB."""
    action_type = (action.get("type") or "").strip()
    if action_type in DANGEROUS_ACTIONS and action.get("confirm") is not True:
        audit_log("admin_action_confirmation_required", admin_id, action_type, action.get("userId") or action.get("email") or action.get("projectId"), action)
        return {
            "success": False,
            "message": f"Confirmation required before executing '{action_type}'. Confirm explicitly to proceed.",
        }

    try:
        # ── 1. EXECUTIVE REPORTS & ANALYTICS ───────────────────────────────
        if action_type in ("get_executive_dashboard", "get_revenue_report", "generate_report", "get_db_stats"):
            data = _build_executive_dashboard()
            return {"success": True, "message": "Live executive operations report compiled.", "data": data, "format": "json"}

        elif action_type == "send_admin_report_email":
            data = _build_executive_dashboard()
            from utils.mailer import send_admin_email
            body = "<h3>THE QS HUB — Executive Operations Report</h3><pre>" + json.dumps(data, indent=2, ensure_ascii=False) + "</pre>"
            sent = send_admin_email("THE QS HUB — Live Operations Report", body)
            return {
                "success": bool(sent),
                "message": "Executive report emailed to admin successfully." if sent else "SMTP is not configured on server; report shown below instead.",
                "data": data,
                "format": "json",
            }

        # ── 2. USER MANAGEMENT ─────────────────────────────────────────────
        elif action_type in ("search_users", "list_users"):
            q = (action.get("query") or "").strip()
            limit = min(100, max(1, int(action.get("limit", 30))))
            if q:
                df = safe_query(
                    "SELECT id, email, role, created_at FROM qto_users WHERE LOWER(email) LIKE LOWER(%s) ORDER BY id DESC LIMIT %s",
                    (f"%{q}%", limit),
                )
            else:
                df = safe_query("SELECT id, email, role, created_at FROM qto_users ORDER BY id DESC LIMIT %s", (limit,))
            rows = df.to_dict("records") if not df.empty else []
            return {"success": True, "message": f"Found {len(rows)} user(s).", "data": rows, "format": "table"}

        elif action_type in ("get_user_full_profile", "get_user"):
            u = _resolve_user(action)
            if not u:
                return {"success": False, "message": "User not found. Provide a valid userId or email."}
            uid = int(u["id"])
            u_dict = {"id": uid, "role": u["role"], "email": u["email"]}
            tools_status = {}
            for feat in VALID_FEATURES:
                sub = get_active_subscription(uid, feat)
                ent = project_entitlement(u_dict, feat)
                tools_status[feat] = {
                    "plan": get_plan_for_user(uid, u["role"], feat).name,
                    "sub_status": sub["status"] if sub else "inactive",
                    "period_end": str(sub.get("current_period_end")) if sub else None,
                    "used_this_month": ent["used"],
                    "monthly_base": ent["base"],
                    "extra_credits": ent["credits"],
                    "free_trial_left": ent["free_left"],
                    "can_create": ent["can_create"],
                }
            q_cnt = safe_query("SELECT COUNT(*) AS c FROM qto_projects WHERE user_id=%s", (uid,))
            m_df = safe_query("SELECT feature, COUNT(*) AS c FROM qto_module_projects WHERE user_id=%s GROUP BY feature", (uid,))
            c_df = safe_query("SELECT id, status, complaint_text, created_at FROM qto_customer_complaints WHERE user_id=%s ORDER BY id DESC LIMIT 5", (uid,))
            return {
                "success": True,
                "message": f"360° profile retrieved for {u['email']} (ID #{uid}).",
                "data": {
                    "user": u,
                    "tools_entitlements": tools_status,
                    "saved_qto_projects": int(q_cnt.iloc[0]["c"]) if not q_cnt.empty else 0,
                    "saved_module_projects": m_df.to_dict("records") if not m_df.empty else [],
                    "recent_tickets": c_df.to_dict("records") if not c_df.empty else [],
                },
                "format": "json",
            }

        elif action_type == "block_user":
            u = _resolve_user(action)
            if not u:
                return {"success": False, "message": "User not found."}
            uid = int(u["id"])
            reason = action.get("reason", "Blocked by Operations Director")
            ok, msg = safe_execute("UPDATE qto_users SET role='blocked' WHERE id=%s", (uid,))
            if ok:
                audit_log("admin_block_user", admin_id, "user", uid, {"reason": reason})
                return {"success": True, "message": f"User #{uid} ({u['email']}) blocked. Reason: {reason}"}
            return {"success": False, "message": f"Failed to block user: {msg}"}

        elif action_type == "unblock_user":
            u = _resolve_user(action)
            if not u:
                return {"success": False, "message": "User not found."}
            uid = int(u["id"])
            ok, msg = safe_execute("UPDATE qto_users SET role='user' WHERE id=%s", (uid,))
            if ok:
                audit_log("admin_unblock_user", admin_id, "user", uid)
                return {"success": True, "message": f"User #{uid} ({u['email']}) unblocked."}
            return {"success": False, "message": f"Failed to unblock user: {msg}"}

        elif action_type == "update_user_role":
            u = _resolve_user(action)
            new_role = (action.get("role") or "").strip().lower()
            if not u or new_role not in ("user", "admin", "blocked"):
                return {"success": False, "message": "Provide a valid user (userId/email) and role (user | admin | blocked)."}
            uid = int(u["id"])
            ok, msg = safe_execute("UPDATE qto_users SET role=%s WHERE id=%s", (new_role, uid))
            if ok:
                audit_log("admin_update_user_role", admin_id, "user", uid, {"role": new_role})
                return {"success": True, "message": f"User #{uid} ({u['email']}) role changed to '{new_role}'."}
            return {"success": False, "message": f"Failed: {msg}"}

        elif action_type == "delete_user":
            u = _resolve_user(action)
            if not u:
                return {"success": False, "message": "User not found."}
            uid = int(u["id"])
            if uid == admin_id:
                return {"success": False, "message": "Safety lock: you cannot delete your own admin account."}
            for tbl in (
                "qto_subscriptions", "qto_usage_logs", "qto_projects",
                "qto_active_projects", "qto_module_projects",
                "qto_customer_complaints", "qto_agent_conversations",
            ):
                safe_execute(f"DELETE FROM {tbl} WHERE user_id=%s", (uid,))
            ok, msg = safe_execute("DELETE FROM qto_users WHERE id=%s", (uid,))
            if ok:
                _clear_plan_caches()
                audit_log("admin_delete_user", admin_id, "user", uid, {"email": u["email"]})
                return {"success": True, "message": f"User #{uid} ({u['email']}) and all associated records deleted."}
            return {"success": False, "message": f"Delete failed: {msg}"}

        # ── 3. PER-TOOL SUBSCRIPTIONS & CREDITS ────────────────────────────
        elif action_type == "list_subscriptions":
            df = safe_query(
                """
                SELECT s.id, s.user_id, u.email, s.feature, s.plan_tier, s.provider, s.status, s.current_period_end
                FROM qto_subscriptions s
                JOIN qto_users u ON s.user_id = u.id
                ORDER BY s.id DESC LIMIT 100
                """
            )
            rows = df.to_dict("records") if not df.empty else []
            return {"success": True, "message": f"Found {len(rows)} subscription record(s).", "data": rows, "format": "table"}

        elif action_type in ("grant_subscription", "give_free_subscription", "update_subscription"):
            u = _resolve_user(action)
            if not u:
                return {"success": False, "message": "User not found. Provide userId or email."}
            uid = int(u["id"])
            feature = (action.get("feature") or "qto").strip().lower()
            if feature not in VALID_FEATURES:
                return {"success": False, "message": f"Invalid feature '{feature}'. Must be qto, programme, or cashflow."}
            tier = int(action.get("planTier") or action.get("planId") or action.get("plan_tier") or 2)
            if tier not in (2, 3, 4):
                return {"success": False, "message": "Plan tier must be 2 (Professional), 3 (Business), or 4 (Studio)."}
            days = max(1, int(action.get("days", 30)))
            period_end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

            existing = safe_query(
                "SELECT id FROM qto_subscriptions WHERE user_id=%s AND feature=%s ORDER BY id DESC LIMIT 1",
                (uid, feature),
            )
            if not existing.empty:
                sub_id = int(existing.iloc[0]["id"])
                ok, msg = safe_execute(
                    "UPDATE qto_subscriptions SET plan_tier=%s, status='active', provider='admin_grant', current_period_end=%s WHERE id=%s",
                    (tier, period_end, sub_id),
                )
            else:
                ok, msg = safe_execute(
                    "INSERT INTO qto_subscriptions (user_id, feature, plan_tier, provider, provider_subscription_id, status, current_period_end) VALUES (%s, %s, %s, 'admin_grant', %s, 'active', %s)",
                    (uid, feature, tier, f"admin_{uid}_{feature}_{int(datetime.now().timestamp())}", period_end),
                )
            if ok:
                _clear_plan_caches()
                audit_log("admin_grant_subscription", admin_id, "user", uid, {"feature": feature, "tier": tier, "days": days})
                return {"success": True, "message": f"Granted {PLANS[tier].name} (Tier {tier}) for '{feature}' to {u['email']} for {days} days."}
            return {"success": False, "message": f"Failed to grant subscription: {msg}"}

        elif action_type == "grant_extra_credits":
            u = _resolve_user(action)
            if not u:
                return {"success": False, "message": "User not found."}
            uid = int(u["id"])
            feature = (action.get("feature") or "qto").strip().lower()
            col = FEATURE_EXTRA_COL.get(feature)
            if not col:
                return {"success": False, "message": f"Invalid feature '{feature}'. Must be qto, programme, or cashflow."}
            credits = max(1, min(100, int(action.get("credits", 1))))
            ok, msg = safe_execute(f"UPDATE qto_users SET {col} = COALESCE({col}, 0) + %s WHERE id=%s", (credits, uid))
            if ok:
                new_bal = extra_projects_for(uid, feature)
                audit_log("admin_grant_credits", admin_id, "user", uid, {"feature": feature, "added": credits, "new_balance": new_bal})
                return {"success": True, "message": f"Added +{credits} extra '{feature}' project credit(s) to {u['email']}. New credit balance: {new_bal}."}
            return {"success": False, "message": f"Failed: {msg}"}

        elif action_type == "cancel_subscription":
            u = _resolve_user(action)
            if not u:
                return {"success": False, "message": "User not found."}
            uid = int(u["id"])
            feature = (action.get("feature") or "").strip().lower()
            if feature in VALID_FEATURES:
                ok, msg = safe_execute("UPDATE qto_subscriptions SET status='cancelled' WHERE user_id=%s AND feature=%s", (uid, feature))
                scope = feature
            else:
                ok, msg = safe_execute("UPDATE qto_subscriptions SET status='cancelled' WHERE user_id=%s", (uid,))
                scope = "all tools"
            if ok:
                _clear_plan_caches()
                audit_log("admin_cancel_subscription", admin_id, "user", uid, {"scope": scope})
                return {"success": True, "message": f"Cancelled active subscriptions ({scope}) for {u['email']}."}
            return {"success": False, "message": f"Failed: {msg}"}

        # ── 4. PROJECTS SUPERVISION (ALL 3 TOOLS) ──────────────────────────
        elif action_type in ("list_all_projects", "list_projects"):
            feature = (action.get("feature") or "all").strip().lower()
            limit = min(100, max(1, int(action.get("limit", 30))))
            results = []
            if feature in ("all", "qto"):
                df_q = safe_query(
                    "SELECT p.id, 'qto' AS tool, p.name, p.date, p.current_step, u.email FROM qto_projects p JOIN qto_users u ON p.user_id=u.id ORDER BY p.id DESC LIMIT %s",
                    (limit,),
                )
                if not df_q.empty:
                    results.extend(df_q.to_dict("records"))
            if feature in ("all", "programme", "cashflow"):
                if feature == "all":
                    df_m = safe_query(
                        "SELECT m.id, m.feature AS tool, m.name, m.date, u.email FROM qto_module_projects m JOIN qto_users u ON m.user_id=u.id ORDER BY m.id DESC LIMIT %s",
                        (limit,),
                    )
                else:
                    df_m = safe_query(
                        "SELECT m.id, m.feature AS tool, m.name, m.date, u.email FROM qto_module_projects m JOIN qto_users u ON m.user_id=u.id WHERE m.feature=%s ORDER BY m.id DESC LIMIT %s",
                        (feature, limit),
                    )
                if not df_m.empty:
                    results.extend(df_m.to_dict("records"))
            return {"success": True, "message": f"Found {len(results)} project(s).", "data": results[:limit], "format": "table"}

        elif action_type == "delete_project":
            pid = action.get("projectId")
            feature = (action.get("feature") or "qto").strip().lower()
            if not pid:
                return {"success": False, "message": "Missing projectId."}
            if feature == "qto":
                safe_execute("DELETE FROM qto_active_projects WHERE project_id=%s", (int(pid),))
                ok, msg = safe_execute("DELETE FROM qto_projects WHERE id=%s", (int(pid),))
            elif feature in ("programme", "cashflow"):
                ok, msg = safe_execute("DELETE FROM qto_module_projects WHERE id=%s AND feature=%s", (int(pid), feature))
            else:
                return {"success": False, "message": "Invalid feature. Use qto, programme, or cashflow."}
            if ok:
                audit_log("admin_delete_project", admin_id, feature, int(pid))
                return {"success": True, "message": f"Deleted {feature} project #{pid}."}
            return {"success": False, "message": f"Failed: {msg}"}

        # ── 5. CUSTOMER SUPPORT, INQUIRIES, FEEDBACK, REVIEWS & AI RULES ───
        elif action_type == "list_complaints":
            status = (action.get("status") or "open").strip().lower()
            if status == "all":
                df = safe_query("SELECT c.id, u.email, c.status, c.complaint_text, c.created_at FROM qto_customer_complaints c LEFT JOIN qto_users u ON c.user_id=u.id ORDER BY c.id DESC LIMIT 30")
            else:
                df = safe_query("SELECT c.id, u.email, c.status, c.complaint_text, c.created_at FROM qto_customer_complaints c LEFT JOIN qto_users u ON c.user_id=u.id WHERE c.status=%s ORDER BY c.id DESC LIMIT 30", (status,))
            rows = df.to_dict("records") if not df.empty else []
            return {"success": True, "message": f"Found {len(rows)} complaint ticket(s) (status={status}).", "data": rows, "format": "table"}

        elif action_type == "resolve_complaint":
            cid = action.get("complaintId") or action.get("ticketId")
            if not cid:
                return {"success": False, "message": "Missing complaintId."}
            ok, msg = safe_execute("UPDATE qto_customer_complaints SET status='resolved' WHERE id=%s", (int(cid),))
            return {"success": bool(ok), "message": f"Support ticket #{cid} marked resolved." if ok else f"Failed: {msg}"}

        elif action_type == "list_inquiries":
            df = safe_query("SELECT id, name, email, subject, category, status, created_at FROM qto_inquiries ORDER BY id DESC LIMIT 30")
            rows = df.to_dict("records") if not df.empty else []
            return {"success": True, "message": f"Found {len(rows)} inquiry(ies).", "data": rows, "format": "table"}

        elif action_type == "update_inquiry_status":
            iid = action.get("inquiryId")
            st = (action.get("status") or "resolved").strip().lower()
            if not iid or st not in ("new", "in_progress", "resolved"):
                return {"success": False, "message": "Provide inquiryId and status (new | in_progress | resolved)."}
            ok, msg = safe_execute("UPDATE qto_inquiries SET status=%s WHERE id=%s", (st, int(iid)))
            return {"success": bool(ok), "message": f"Inquiry #{iid} updated to '{st}'." if ok else f"Failed: {msg}"}

        elif action_type == "get_tool_feedback":
            s_df = safe_query("SELECT tool_name, COUNT(*) AS total, ROUND(AVG(rating), 2) AS avg_rating FROM qto_project_feedback GROUP BY tool_name")
            r_df = safe_query("SELECT f.id, u.email, f.tool_name, f.project_name, f.rating, f.reason, f.created_at FROM qto_project_feedback f LEFT JOIN qto_users u ON f.user_id=u.id ORDER BY f.id DESC LIMIT 20")
            return {
                "success": True,
                "message": "Tool feedback summary retrieved.",
                "data": {
                    "summary": s_df.to_dict("records") if not s_df.empty else [],
                    "recent": r_df.to_dict("records") if not r_df.empty else [],
                },
                "format": "json",
            }

        elif action_type == "list_reviews":
            df = safe_query("SELECT id, user_name, company, rating, review_title, is_approved, is_featured, created_at FROM qto_reviews ORDER BY id DESC LIMIT 30")
            rows = df.to_dict("records") if not df.empty else []
            return {"success": True, "message": f"Found {len(rows)} review(s).", "data": rows, "format": "table"}

        elif action_type == "moderate_review":
            rid = action.get("reviewId")
            act = (action.get("action") or "").strip().lower()
            if not rid or act not in ("approve", "unapprove", "feature", "unfeature", "delete"):
                return {"success": False, "message": "Provide reviewId and action (approve|unapprove|feature|unfeature|delete)."}
            if act == "delete":
                ok, msg = safe_execute("DELETE FROM qto_reviews WHERE id=%s", (int(rid),))
            elif act in ("approve", "unapprove"):
                ok, msg = safe_execute("UPDATE qto_reviews SET is_approved=%s WHERE id=%s", (1 if act == "approve" else 0, int(rid)))
            else:
                ok, msg = safe_execute("UPDATE qto_reviews SET is_featured=%s WHERE id=%s", (1 if act == "feature" else 0, int(rid)))
            return {"success": bool(ok), "message": f"Review #{rid}: {act} completed." if ok else f"Failed: {msg}"}

        elif action_type == "list_pending_rules":
            df = safe_query("SELECT id, user_id, original_text, mapped_category, created_at FROM qto_memory_rules WHERE status='pending' ORDER BY id ASC LIMIT 50")
            rows = df.to_dict("records") if not df.empty else []
            return {"success": True, "message": f"Found {len(rows)} pending AI learning rule(s).", "data": rows, "format": "table"}

        elif action_type == "moderate_memory_rule":
            rid = action.get("ruleId")
            dec = (action.get("decision") or "").strip().lower()
            if not rid or dec not in ("approve", "reject"):
                return {"success": False, "message": "Provide ruleId and decision (approve | reject)."}
            if dec == "approve":
                ok, msg = safe_execute("UPDATE qto_memory_rules SET status='global', user_id=NULL WHERE id=%s", (int(rid),))
            else:
                ok, msg = safe_execute("DELETE FROM qto_memory_rules WHERE id=%s", (int(rid),))
            return {"success": bool(ok), "message": f"Memory rule #{rid} {dec}d." if ok else f"Failed: {msg}"}

        # ── 6. LIVE MARKET PRICES OPERATIONS ───────────────────────────────
        elif action_type == "sync_market_prices":
            from utils.market_prices_logic import update_db_prices
            ok, msg = update_db_prices(force_live=True)
            audit_log("admin_sync_market_prices", admin_id, "market", "all", {"ok": ok, "msg": msg})
            return {"success": bool(ok), "message": msg}

        elif action_type == "list_material_prices":
            from utils.market_prices_logic import get_live_market_snapshot
            snap = get_live_market_snapshot(category=action.get("category", "all"), compare=True)
            return {"success": True, "message": f"{len(snap['prices'])} items (sync_mode={snap['meta']['sync_mode']}, last_sync={snap['meta']['last_live_sync']})", "data": snap["prices"], "format": "table"}

        elif action_type == "update_material_price":
            code = action.get("code") or action.get("item_name")
            emirate = action.get("emirate") or "dubai"
            price = action.get("price") or action.get("rate_aed")
            if not code or price is None:
                return {"success": False, "message": "Provide code/item_name, emirate (e.g. dubai/abudhabi/all), and numeric price."}
            from utils.market_prices_logic import set_manual_material_price
            ok, msg = set_manual_material_price(str(code), str(emirate), float(price))
            if ok:
                audit_log("admin_update_material_price", admin_id, "market", str(code), {"emirate": emirate, "price": price})
            return {"success": bool(ok), "message": msg}

        # ── 7. SYSTEM HEALTH, SAFE MAINTENANCE, EMAIL & REFUNDS ────────────
        elif action_type == "get_system_health":
            db_ok = False
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                db_ok = True
            except Exception:
                pass
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(root_dir, "_qto_cache")
            cache_files = 0
            cache_mb = 0.0
            if os.path.isdir(cache_dir):
                for dp, _, fns in os.walk(cache_dir):
                    for fn in fns:
                        cache_files += 1
                        try:
                            cache_mb += os.path.getsize(os.path.join(dp, fn)) / (1024 * 1024)
                        except OSError:
                            pass
            mgr = get_key_manager()
            keys_count = len(getattr(mgr, "_keys", []))
            status_summary = mgr.get_status_summary() if hasattr(mgr, "get_status_summary") else {"total_keys": keys_count}
            return {
                "success": True,
                "message": "Live system & API key pool diagnostics retrieved.",
                "data": {
                    "Database Connected": db_ok,
                    "DB Engine": "SQLite (Local)" if is_sqlite() else "TiDB Cloud (MySQL)",
                    "Cache Directory Files": cache_files,
                    "Cache Disk Usage (MB)": round(cache_mb, 2),
                    "Gemini Keys Configured": keys_count,
                    "KeyManager Pool Status": status_summary,
                },
                "format": "json",
            }

        elif action_type == "run_safe_maintenance":
            from utils.garbage_collection import purge_expired_cache
            removed_dirs = purge_expired_cache()
            cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
            ok_logs, msg_logs = safe_execute("DELETE FROM qto_usage_logs WHERE created_at < %s", (cutoff,))
            audit_log("admin_safe_maintenance", admin_id, "system", "cleanup", {"removed_cache_dirs": removed_dirs})
            return {
                "success": True,
                "message": f"Safe maintenance complete: purged {removed_dirs} expired cache folder(s) and pruned usage logs older than 90 days (active subscriptions untouched). Logs cleanup ok={ok_logs}.",
            }

        elif action_type == "send_user_email":
            to_email = (action.get("email") or "").strip()
            subject = (action.get("subject") or "Message from THE QS HUB").strip()
            body = (action.get("body") or action.get("content") or "").strip()
            if not to_email or not body:
                return {"success": False, "message": "Provide email, subject, and body."}
            from utils.mailer import send_custom_email
            html = f"<div style='font-family:Arial,sans-serif;line-height:1.6'>{body.replace(chr(10), '<br/>')}</div>"
            sent = send_custom_email(subject, html, to_email)
            audit_log("admin_send_email", admin_id, "email", to_email, {"subject": subject, "sent": sent})
            return {
                "success": bool(sent),
                "message": f"Email sent to {to_email}." if sent else f"SMTP is not configured on the server — email to {to_email} was NOT sent.",
            }

        elif action_type == "verify_user_email":
            target_email = (action.get("email") or "").strip().lower()
            if not target_email:
                return {"success": False, "message": "Missing email parameter."}
            ok, err = safe_execute(
                "UPDATE qto_users SET email_verified=1, verification_token_hash=NULL WHERE email=%s",
                (target_email,),
            )
            if ok:
                audit_log("admin_verify_email", admin_id, "user", target_email)
            return {
                "success": bool(ok),
                "message": f"Email verified manually for {target_email}." if ok else f"Failed to verify email: {err}",
            }

        elif action_type == "issue_refund":
            target_email = (action.get("email") or "").strip()
            if not target_email:
                return {"success": False, "message": "Missing email parameter for refund."}
            from utils.payments import issue_dodo_refund
            ok, msg = issue_dodo_refund(target_email)
            if ok:
                audit_log("admin_issue_refund", admin_id, "user", target_email)
            return {"success": bool(ok), "message": f"Refund result for {target_email}: {msg}"}

        else:
            return {"success": False, "message": f"Unknown action type '{action_type}'."}

    except Exception as e:
        return {"success": False, "message": f"Error executing action '{action_type}': {str(e)}"}


def process_admin_message(prompt: str, chat_history: list, admin_name: str, admin_id: int) -> Tuple[str, Optional[dict]]:
    """Run the AI Operations Director with full 20-key rotation and real action execution."""
    manager = get_key_manager()
    max_attempts = max(6, min(len(getattr(manager, "_keys", [])) * 2, 16))

    system_prompt = f"""You are the **AI Operations Director & Platform Supervisor** for **THE QS HUB** (UAE's AI Quantity Surveying platform with 3 independent tools: `qto`, `programme`, `cashflow`).
Always address the founder respectfully as "Eng. {admin_name}" (or "م. {admin_name}" in Arabic).

=== YOUR REAL OPERATIONAL DUTIES & VERIFIED TOOLS ===
Every tool below executes REAL live operations against THE QS HUB database, Dodo Payments, SMTP, and live Google Search Market Prices. NEVER claim to perform an action that isn't in this list!

READ / SUPERVISION TOOLS (no confirmation needed):
- `get_executive_dashboard` — Full live CEO report: users, REAL MRR revenue by tool & tier, projects across QTO/Programme/CashFlow, open complaints, inquiries, feedback ratings, visitor traffic 24h.
- `search_users` — {{"type":"search_users", "query":"optional email substring", "limit":30}}
- `get_user_full_profile` — {{"type":"get_user_full_profile", "email":"user@x.com"}} (or `"userId": 5`) — 360° status across all 3 tools, credits, projects & tickets.
- `list_subscriptions` — {{"type":"list_subscriptions"}}
- `list_all_projects` — {{"type":"list_all_projects", "feature":"all|qto|programme|cashflow", "limit":30}}
- `list_complaints` — {{"type":"list_complaints", "status":"open|resolved|all"}}
- `resolve_complaint` — {{"type":"resolve_complaint", "complaintId": 12}}
- `list_inquiries` — {{"type":"list_inquiries"}}
- `update_inquiry_status` — {{"type":"update_inquiry_status", "inquiryId": 4, "status":"new|in_progress|resolved"}}
- `get_tool_feedback` — {{"type":"get_tool_feedback"}}
- `list_reviews` — {{"type":"list_reviews"}}
- `moderate_review` — {{"type":"moderate_review", "reviewId": 3, "action":"approve|unapprove|feature|unfeature|delete"}}
- `list_pending_rules` — {{"type":"list_pending_rules"}}
- `moderate_memory_rule` — {{"type":"moderate_memory_rule", "ruleId": 7, "decision":"approve|reject"}}
- `list_material_prices` — {{"type":"list_material_prices", "category":"all|steel|concrete|labor|..."}}
- `sync_market_prices` — {{"type":"sync_market_prices"}} (runs REAL live Google Search UAE price refresh!)
- `update_material_price` — {{"type":"update_material_price", "code":"STL003", "emirate":"dubai|abudhabi|all", "price":2950}}
- `get_system_health` — {{"type":"get_system_health"}} (DB, cache disk usage, all 20 Gemini API keys pool health!)
- `send_admin_report_email` — {{"type":"send_admin_report_email"}}

PRIVILEGED / DESTRUCTIVE TOOLS (MUST ask founder to confirm first; include `"confirm": true` ONLY after explicit confirmation):
- `grant_subscription` — {{"type":"grant_subscription", "email":"...", "feature":"qto|programme|cashflow", "planTier":2, "days":30, "confirm":true}}
- `grant_extra_credits` — {{"type":"grant_extra_credits", "email":"...", "feature":"qto|programme|cashflow", "credits":1, "confirm":true}}
- `cancel_subscription` — {{"type":"cancel_subscription", "email":"...", "feature":"qto|programme|cashflow", "confirm":true}}
- `block_user` / `unblock_user` / `verify_user_email` / `update_user_role` / `delete_user`
- `delete_project` — {{"type":"delete_project", "projectId": 10, "feature":"qto|programme|cashflow", "confirm":true}}
- `run_safe_maintenance` — {{"type":"run_safe_maintenance", "confirm":true}}
- `send_user_email` — {{"type":"send_user_email", "email":"...", "subject":"...", "body":"...", "confirm":true}}
- `issue_refund` — {{"type":"issue_refund", "email":"...", "confirm":true}}

=== EXECUTION PROTOCOL ===
1. Whenever a request requires live site data or an operation, ALWAYS emit ONE clean JSON command on its own line starting with `ACTION:` (no markdown code fences around it):
   ACTION: {{"type": "get_executive_dashboard"}}
2. NEVER invent fake numbers, fake revenue, or fake user lists — always invoke the real tool!
3. For destructive/privileged actions, first state the exact target and ask Eng. {admin_name} for confirmation; once they confirm in the next message, emit the ACTION with `"confirm": true`.
4. Reply concisely and authoritatively in the EXACT language used by the founder (Arabic for Arabic, English for English)."""

    contents = []
    for msg in chat_history[-12:]:
        r = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=r, parts=[types.Part.from_text(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

    last_err = ""
    for _ in range(max_attempts):
        api_key, model_name = manager.get_key_and_model()
        if not api_key or api_key == "NO_API_KEY_FOUND":
            return "No AI API key configured on the server.", None
        try:
            client = genai.Client(api_key=api_key, http_options={"timeout": 40.0, "api_version": "v1beta"})
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3),
            )
            reply = (response.text or "").strip()
            action_result = None

            action_match = re.search(r"ACTION:\s*(\{.*?\})", reply, re.DOTALL)
            if action_match:
                try:
                    raw_json = action_match.group(1).strip()
                    # Handle nested braces safely if needed
                    action_data = json.loads(raw_json)
                    action_result = execute_admin_action(admin_id, action_data)
                except Exception:
                    # Fallback greedy brace match for nested JSON
                    m2 = re.search(r"ACTION:\s*(\{.*\})", reply, re.DOTALL)
                    if m2:
                        try:
                            action_data = json.loads(m2.group(1).strip())
                            action_result = execute_admin_action(admin_id, action_data)
                        except Exception as ex:
                            action_result = {"success": False, "message": f"Failed to parse action JSON: {ex}"}

            # Strip raw ACTION JSON line cleanly so the founder never sees raw JSON commands
            clean_reply = re.sub(r"ACTION:\s*\{.*\}", "", reply, flags=re.DOTALL).strip()
            if not clean_reply and action_result:
                is_ar = any("\u0600" <= c <= "\u06FF" for c in prompt)
                if action_result.get("success"):
                    clean_reply = (
                        f"تم تنفيذ الأمر بنجاح يا م. {admin_name} — إليك النتائج الحية من النظام:"
                        if is_ar
                        else f"Done, Eng. {admin_name} — live operational results are shown below."
                    )
                else:
                    clean_reply = action_result.get("message") or reply
            return clean_reply or reply, action_result
        except Exception as e:
            last_err = str(e)
            err_low = last_err.lower()
            if "404" in err_low or "not found" in err_low:
                manager.mark_model_unavailable(model_name)
                continue
            if any(tok in err_low for tok in ("429", "quota", "resource_exhausted", "503", "unavailable", "timeout", "deadline", "overloaded")):
                manager.mark_rate_limited(api_key, model_name)
                continue
            break

    return f"AI Operations Director error: {last_err}", None
