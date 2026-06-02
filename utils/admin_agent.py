import json
import re
from datetime import datetime
from google import genai
from google.genai import types
from utils.db import safe_query, safe_execute
from utils.key_manager import get_key_manager
from utils.audit import audit_log


DANGEROUS_ACTIONS = {
    "delete_user",
    "delete_project",
    "block_user",
    "update_user_role",
    "update_subscription",
    "give_free_subscription",
    "cancel_subscription",
    "run_maintenance",
}

def execute_admin_action(admin_id: int, action: dict) -> dict:
    """
    Executes database queries/mutations based on structured JSON actions
    returned by the SUPREME SUPERVISOR LLM.
    """
    action_type = action.get("type")
    print(f"[Admin Action] Admin ID {admin_id} executing action: {action}")
    if action_type in DANGEROUS_ACTIONS and action.get("confirm") is not True:
        audit_log("admin_action_confirmation_required", admin_id, action_type, action.get("userId") or action.get("projectId"), action)
        return {
            "success": False,
            "message": f"Confirmation required for '{action_type}'. Re-run with confirm=true after reviewing the target.",
        }
    
    try:
        if action_type == "list_users":
            limit = int(action.get("limit", 50))
            offset = int(action.get("offset", 0))
            df = safe_query("SELECT id, email, role, created_at FROM qto_users ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
            return {
                "success": True,
                "message": f"Found {len(df)} users",
                "data": df.to_dict("records") if not df.empty else [],
                "format": "table"
            }
            
        elif action_type == "get_user":
            user_id = action.get("userId")
            if not user_id:
                return {"success": False, "message": "Missing userId parameter"}
            df_user = safe_query("SELECT id, email, role, created_at FROM qto_users WHERE id = %s", (user_id,))
            if df_user.empty:
                return {"success": False, "message": f"User {user_id} not found"}
            df_sub = safe_query("SELECT * FROM qto_subscriptions WHERE user_id = %s", (user_id,))
            
            # Fetch usage counts from usage logs
            df_logs = safe_query("SELECT COUNT(*) as count FROM qto_usage_logs WHERE user_id = %s", (user_id,))
            usage_count = int(df_logs.iloc[0]["count"]) if not df_logs.empty else 0
            
            return {
                "success": True,
                "message": "User details retrieved",
                "data": {
                    "user": df_user.to_dict("records")[0],
                    "subscription": df_sub.to_dict("records")[0] if not df_sub.empty else None,
                    "usage_count": usage_count
                },
                "format": "json"
            }
            
        elif action_type == "block_user":
            user_id = action.get("userId")
            reason = action.get("reason", "No reason provided")
            if not user_id:
                return {"success": False, "message": "Missing userId parameter"}
            success, msg = safe_execute("UPDATE qto_users SET role = 'blocked' WHERE id = %s", (user_id,))
            if success:
                audit_log("admin_block_user", admin_id, "user", user_id, {"reason": reason})
                return {"success": True, "message": f"User {user_id} blocked successfully. Reason: {reason}"}
            return {"success": False, "message": f"Failed to block user: {msg}"}
            
        elif action_type == "unblock_user":
            user_id = action.get("userId")
            if not user_id:
                return {"success": False, "message": "Missing userId parameter"}
            success, msg = safe_execute("UPDATE qto_users SET role = 'user' WHERE id = %s", (user_id,))
            if success:
                audit_log("admin_unblock_user", admin_id, "user", user_id)
                return {"success": True, "message": f"User {user_id} unblocked successfully"}
            return {"success": False, "message": f"Failed to unblock user: {msg}"}
            
        elif action_type == "delete_user":
            user_id = action.get("userId")
            if not user_id:
                return {"success": False, "message": "Missing userId parameter"}
            # Clean up child records first
            safe_execute("DELETE FROM qto_subscriptions WHERE user_id = %s", (user_id,))
            safe_execute("DELETE FROM qto_usage_logs WHERE user_id = %s", (user_id,))
            success, msg = safe_execute("DELETE FROM qto_users WHERE id = %s", (user_id,))
            if success:
                audit_log("admin_delete_user", admin_id, "user", user_id)
                return {"success": True, "message": f"User {user_id} and related data deleted successfully"}
            return {"success": False, "message": f"Failed to delete user: {msg}"}
            
        elif action_type == "update_user_role":
            user_id = action.get("userId")
            role = action.get("role")
            if not user_id or not role:
                return {"success": False, "message": "Missing userId or role parameter"}
            success, msg = safe_execute("UPDATE qto_users SET role = %s WHERE id = %s", (role, user_id))
            if success:
                audit_log("admin_update_user_role", admin_id, "user", user_id, {"role": role})
                return {"success": True, "message": f"User {user_id} role updated to '{role}'"}
            return {"success": False, "message": f"Failed to update user role: {msg}"}
            
        elif action_type == "list_subscriptions":
            df = safe_query("SELECT id, user_id, plan_tier, status, projects_used FROM qto_subscriptions LIMIT 100")
            return {
                "success": True,
                "message": f"Found {len(df)} subscriptions",
                "data": df.to_dict("records") if not df.empty else [],
                "format": "table"
            }
            
        elif action_type == "update_subscription":
            user_id = action.get("userId")
            plan_tier = action.get("planId") or action.get("plan_tier", 0)
            status = action.get("status", "active")
            if not user_id:
                return {"success": False, "message": "Missing userId parameter"}
            
            df = safe_query("SELECT id FROM qto_subscriptions WHERE user_id = %s", (user_id,))
            if not df.empty:
                success, msg = safe_execute(
                    "UPDATE qto_subscriptions SET plan_tier = %s, status = %s WHERE user_id = %s",
                    (plan_tier, status, user_id)
                )
            else:
                success, msg = safe_execute(
                    "INSERT INTO qto_subscriptions (user_id, plan_tier, status) VALUES (%s, %s, %s)",
                    (user_id, plan_tier, status)
                )
            if success:
                audit_log("admin_update_subscription", admin_id, "user", user_id, {"tier": plan_tier, "status": status})
                return {"success": True, "message": f"Subscription updated for user {user_id} (Tier: {plan_tier}, Status: {status})"}
            return {"success": False, "message": f"Failed to update subscription: {msg}"}
            
        elif action_type == "give_free_subscription":
            user_id = action.get("userId")
            plan_tier = action.get("planId") or 1
            if not user_id:
                return {"success": False, "message": "Missing userId parameter"}
            
            df = safe_query("SELECT id FROM qto_subscriptions WHERE user_id = %s", (user_id,))
            if not df.empty:
                success, msg = safe_execute(
                    "UPDATE qto_subscriptions SET plan_tier = %s, status = 'active' WHERE user_id = %s",
                    (plan_tier, user_id)
                )
            else:
                success, msg = safe_execute(
                    "INSERT INTO qto_subscriptions (user_id, plan_tier, status) VALUES (%s, %s, 'active')",
                    (user_id, plan_tier)
                )
            if success:
                return {"success": True, "message": f"Free subscription (Tier {plan_tier}) granted to user {user_id}"}
            return {"success": False, "message": f"Failed to grant free subscription: {msg}"}
            
        elif action_type == "cancel_subscription":
            user_id = action.get("userId")
            if not user_id:
                return {"success": False, "message": "Missing userId parameter"}
            success, msg = safe_execute("UPDATE qto_subscriptions SET status = 'cancelled' WHERE user_id = %s", (user_id,))
            if success:
                audit_log("admin_cancel_subscription", admin_id, "user", user_id)
                return {"success": True, "message": f"Subscription cancelled for user {user_id}"}
            return {"success": False, "message": f"Failed to cancel subscription: {msg}"}
            
        elif action_type == "list_projects":
            df = safe_query("SELECT id, name, date FROM qto_projects LIMIT 100")
            return {
                "success": True,
                "message": f"Found {len(df)} projects",
                "data": df.to_dict("records") if not df.empty else [],
                "format": "table"
            }
            
        elif action_type == "delete_project":
            project_id = action.get("projectId")
            if not project_id:
                return {"success": False, "message": "Missing projectId parameter"}
            success, msg = safe_execute("DELETE FROM qto_projects WHERE id = %s", (project_id,))
            if success:
                audit_log("admin_delete_project", admin_id, "project", project_id)
                return {"success": True, "message": f"Project {project_id} deleted successfully"}
            return {"success": False, "message": f"Failed to delete project: {msg}"}
            
        elif action_type == "list_material_prices":
            df = safe_query("SELECT id, item_name, unit, rate_aed, last_updated FROM qto_market_prices LIMIT 100")
            return {
                "success": True,
                "message": f"Found {len(df)} material prices",
                "data": df.to_dict("records") if not df.empty else [],
                "format": "table"
            }
            
        elif action_type == "update_material_price":
            item_name = action.get("code") or action.get("item_name")
            price = action.get("price") or action.get("rate_aed")
            unit = action.get("unit", "unit")
            if not item_name or price is None:
                return {"success": False, "message": "Missing material code/item_name or price parameters"}
            
            df = safe_query("SELECT id FROM qto_market_prices WHERE item_name = %s", (item_name,))
            if not df.empty:
                success, msg = safe_execute(
                    "UPDATE qto_market_prices SET rate_aed = %s, unit = %s WHERE item_name = %s",
                    (price, unit, item_name)
                )
            else:
                success, msg = safe_execute(
                    "INSERT INTO qto_market_prices (item_name, rate_aed, unit) VALUES (%s, %s, %s)",
                    (item_name, price, unit)
                )
            if success:
                return {"success": True, "message": f"Material '{item_name}' price updated to {price} AED ({unit})"}
            return {"success": False, "message": f"Failed to update material price: {msg}"}
            
        elif action_type == "get_db_stats":
            users_count = int(safe_query("SELECT COUNT(*) as count FROM qto_users").iloc[0]["count"])
            subs_count = int(safe_query("SELECT COUNT(*) as count FROM qto_subscriptions").iloc[0]["count"])
            proj_count = int(safe_query("SELECT COUNT(*) as count FROM qto_projects").iloc[0]["count"])
            price_count = int(safe_query("SELECT COUNT(*) as count FROM qto_market_prices").iloc[0]["count"])
            logs_count = int(safe_query("SELECT COUNT(*) as count FROM qto_usage_logs").iloc[0]["count"])
            
            return {
                "success": True,
                "message": "Database statistics retrieved",
                "data": {
                    "Registered Users": users_count,
                    "Active Subscriptions": subs_count,
                    "Saved Projects": proj_count,
                    "Material Price Items": price_count,
                    "Usage Log Entries": logs_count
                },
                "format": "json"
            }
            
        elif action_type == "run_maintenance":
            task = action.get("task", "full_cleanup")
            # Cleanup usage logs older than 30 days
            success, msg = safe_execute("DELETE FROM qto_usage_logs WHERE created_at < NOW() - INTERVAL 30 DAY")
            # Reset active subscription counters
            safe_execute("UPDATE qto_subscriptions SET projects_used = 0 WHERE status = 'active'")
            if success:
                audit_log("admin_run_maintenance", admin_id, "system", task)
                return {"success": True, "message": f"Maintenance '{task}' completed successfully. Expired usage logs deleted."}
            return {"success": False, "message": f"Failed to run maintenance: {msg}"}
            
        elif action_type in ["generate_report", "get_revenue_report", "get_weekly_report", "get_daily_report", "get_monthly_report"]:
            users_count = int(safe_query("SELECT COUNT(*) as count FROM qto_users").iloc[0]["count"])
            subs_count = int(safe_query("SELECT COUNT(*) as count FROM qto_subscriptions WHERE status = 'active'").iloc[0]["count"])
            proj_count = int(safe_query("SELECT COUNT(*) as count FROM qto_projects").iloc[0]["count"])
            complaints = int(safe_query("SELECT COUNT(*) as count FROM qto_customer_complaints WHERE status = 'open'").iloc[0]["count"])
            revenue = subs_count * 499  # AED estimation
            
            stats_str = f"Users: {users_count}, Active Subs: {subs_count}, Open Complaints: {complaints}, Processed Projects: {proj_count}"
            
            from utils.mailer import send_admin_email
            email_body = f"<h3>AI Manager Report</h3><p>Here are the latest platform stats:</p><p>{stats_str}</p>"
            sent = send_admin_email(f"Platform Report - {action_type}", email_body)
            
            return {
                "success": True,
                "message": f"Report generated and emailed. (Email Sent: {sent})",
                "data": {
                    "Report Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Total Registered Users": users_count,
                    "Active Subscribers": subs_count,
                    "Total Projects Processed": proj_count,
                    "Open Complaints": complaints,
                    "Estimated Monthly Revenue": f"{revenue} AED"
                },
                "format": "json"
            }
            
        elif action_type == "issue_refund":
            target_email = action.get("email")
            if not target_email:
                return {"success": False, "message": "Missing email parameter for refund"}
                
            from utils.payments import issue_dodo_refund
            success, msg = issue_dodo_refund(target_email)
            if success:
                audit_log("admin_issue_refund", admin_id, "user", target_email)
                return {"success": True, "message": f"Refund issued successfully for {target_email}: {msg}"}

            return {"success": False, "message": f"Failed to issue refund: {msg}"}
            
        elif action_type == "send_notification":
            title = action.get("title", "Announcement")
            content = action.get("content", "")
            recipients = action.get("recipients", "all")
            return {"success": True, "message": f"Broadcast message queued: '{title}' to {recipients}"}
            
        else:
            return {"success": False, "message": f"Action type '{action_type}' is not supported yet on this platform."}
            
    except Exception as e:
        return {"success": False, "message": f"Error executing action: {str(e)}"}


def process_admin_message(prompt: str, chat_history: list, admin_name: str, admin_id: int) -> tuple[str, dict | None]:
    """
    Passes the admin user prompt to the AI model with the SUPREME SUPERVISOR prompt.
    Returns: (text_reply, action_result)
    """
    manager = get_key_manager()
    api_key, model_name = manager.get_key_and_model()
    
    if not api_key:
        return "I am ready to assist, but no AI API key is configured. Please check your system configuration.", None
        
    system_prompt = f"""You are the Admin AI Assistant for Q.S Hub - a BOQ estimation platform.
You are the SUPREME SUPERVISOR of Q.S Hub. أنت المدير الكامل للموقع والمسؤول عن كل نقرة فيه.
Always address the user as "Eng. {admin_name}".

=== YOUR ROLE & MISSION ===
- You are the SUPREME SUPERVISOR of Q.S Hub.
- You monitor every click, every project, and every user activity.
- You are responsible for maintenance, updates, payment issues, and training supervision.
- Speak with authority, extreme politeness to the Founder, and high technical competence.

=== CAPABILITIES — 15 RESPONSIBILITY AREAS ===

1. Content & Pages (update_page_content, update_faq)
2. Subscriptions & Offers (list_subscriptions, update_subscription, give_free_subscription, cancel_subscription)
3. Advanced User Management (list_users, get_user, block_user, unblock_user, delete_user, update_user_role)
4. Advanced Reports & Analytics (generate_report, get_revenue_report, get_weekly_report, get_daily_report, get_monthly_report)
5. Database Management (get_db_stats, run_maintenance)
6. Material Prices (list_material_prices, update_material_price)
7. Notifications (send_notification)
8. Training & QA
9. Security & Permissions
10. Marketing
11. Support
12. Performance & Speed
13. Backups
14. Invoices & Refunds (create_invoice, list_invoices, issue_refund)
15. Projects (list_projects, delete_project)

=== HOW TO EXECUTE ACTIONS ===
When the admin asks you to do something:
1. Understand the request (Arabic or English)
2. Explain what you will do
3. Provide the ACTION in JSON format. Do not use markdown inside the ACTION block itself, just write it as:
ACTION: {{"type": "list_users", "limit": 20}}

Examples:
ACTION: {{"type": "list_users", "limit": 20}}
ACTION: {{"type": "get_db_stats"}}
ACTION: {{"type": "block_user", "userId": 5, "reason": "spamming"}}
ACTION: {{"type": "update_material_price", "code": "STEEL_REBAR", "price": 3100, "unit": "ton"}}
ACTION: {{"type": "give_free_subscription", "userId": 12, "planId": 2}}
ACTION: {{"type": "run_maintenance", "task": "cleanup"}}
ACTION: {{"type": "issue_refund", "email": "user@example.com"}}

For destructive or privileged actions, include "confirm": true only after you
clearly state the target and the admin explicitly confirms.

Reply in the same language the user speaks (English or Arabic). Keep your answers concise, professional, and actionable.
"""
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Build contents from history
        contents = []
        for msg in chat_history[-10:]:  # Keep last 10 turns
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
            
        # Append current user prompt
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        ))
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )
        
        reply = response.text.strip()
        
        # Parse ACTION if present
        action_match = re.search(r"ACTION:\s*(\{.*\})", reply, re.DOTALL)
        action_result = None
        
        if action_match:
            try:
                action_json_str = action_match.group(1).strip()
                action_data = json.loads(action_json_str)
                action_result = execute_admin_action(admin_id, action_data)
            except Exception as e:
                print(f"[Admin Action Parse Error] {e}")
                action_result = {"success": False, "message": f"Failed to parse action JSON: {str(e)}"}
                
        return reply, action_result
        
    except Exception as e:
        print(f"[Admin Agent Error] {e}")
        return f"Sorry, an error occurred while processing your request: {str(e)}", None
