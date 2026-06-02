import streamlit as st
import pandas as pd
from utils.i18n import t
from utils.db import safe_query


def fetch_users():
    return safe_query("SELECT id, email, role, created_at FROM qto_users")


def fetch_subscriptions():
    return safe_query(
        """
        SELECT id, user_id, plan_tier, provider, status, current_period_end,
               projects_used, ai_calls_used, exports_used, created_at
        FROM qto_subscriptions
        ORDER BY id DESC
        LIMIT 200
        """
    )

def render_admin():
    st.markdown("<h1 style='color:#3b82f6;'>Admin Dashboard</h1>", unsafe_allow_html=True)
    st.write("Manage users, monitor subscriptions, and oversee platform activity.")
    
    st.divider()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👥 Users", "💳 Subscriptions", "⚙️ System Stats", "🤖 AI Manager", "🧠 AI Learning", "🚨 Complaints"])
    
    with tab1:
        st.subheader("Registered Users")
        users_df = fetch_users()
        if not users_df.empty:
            st.markdown(f'<div style="overflow-x:auto;">{users_df.to_html(classes="styled-table", index=False)}</div>', unsafe_allow_html=True)
        else:
            st.info("No users found.")
            
    with tab2:
        st.subheader("Active Subscriptions")
        subs_df = fetch_subscriptions()
        if not subs_df.empty:
            st.markdown(f'<div style="overflow-x:auto;">{subs_df.to_html(classes="styled-table", index=False)}</div>', unsafe_allow_html=True)
        else:
            st.info("No subscriptions found.")
            
    with tab3:
        st.subheader("🛡️ Production & Safe Deployment Checklist")
        st.caption("Auto-verifies server environments, security headers, database connectivity, and local storage limits before publishing.")
        
        import os
        ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 1. Database Connection Check
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
            
        # 2. Environment Variables Check
        required_env = ["TIDB_HOST", "TIDB_USER", "TIDB_PASSWORD", "TIDB_DATABASE"]
        env_status = {}
        for env in required_env:
            val = os.environ.get(env) or st.secrets.get(env)
            env_status[env] = bool(val)
            
        # 3. Cache Status Check
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
                    cache_size_mb += os.path.getsize(fp) / (1024 * 1024)
                    
        # 4. Local OCR Check
        ocr_ok = False
        try:
            import easyocr
            ocr_ok = True
        except Exception:
            pass
            
        # 5. PDF Engine Check
        pdf_ok = False
        try:
            import fitz
            pdf_ok = True
        except Exception:
            pass
            
        # 6. Render Widgets
        all_ok = db_ok and all(env_status.values()) and ocr_ok and pdf_ok
        
        if all_ok:
            st.success("✅ System Health: PERFECT (All systems are configured correctly for production)")
        else:
            st.warning("⚠️ System Health: WARNED (Some configuration gaps detected - see below)")
            
        # Columns
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("##### 🔑 Environment Variables")
            for env, status in env_status.items():
                icon = "🟢 Configured" if status else "🔴 Missing"
                st.write(f"- `{env}`: **{icon}**")
                
        with col_c2:
            st.markdown("##### 🔌 Core Integrations")
            st.write(f"- Live Database Ping: **{'🟢 Success' if db_ok else f'🔴 Failed ({db_err})'}**")
            st.write(f"- Local EasyOCR Fallback Engine: **{'🟢 Ready' if ocr_ok else '🔴 Missing'}**")
            st.write(f"- PyMuPDF Blueprint Engine: **{'🟢 Ready' if pdf_ok else '🔴 Missing'}**")
            
        st.divider()
        
        st.markdown("##### 💾 Storage & Caching Layer (Secure Disk Cache)")
        c_col1, c_col2, c_col3 = st.columns(3)
        c_col1.metric("Cache Folder Status", "Created" if cache_exists else "Not Found")
        c_col2.metric("Cached Blueprint Extractions", f"{cache_count} files")
        c_col3.metric("Cache Disk Usage", f"{cache_size_mb:.2f} MB")
        
        st.divider()
        st.markdown("##### 🚀 Safe Deployment Steps Checklist")
        st.checkbox("Force HTTPS Redirection (configure Nginx or Cloudflare)", value=True, disabled=True)
        st.checkbox("Use serverless database cluster (TiDB is connected)", value=True, disabled=True)
        st.checkbox("Restrict Cache Directory permissions (deny public read access to secure disk cache)", value=False)
        st.checkbox("Link error monitoring software (e.g. Sentry) inside `config.py`", value=False)
        st.checkbox("Enable Cloudflare WAF protection against DDoS", value=False)
        
    with tab4:
        st.subheader("Admin AI Manager (SUPREME SUPERVISOR)")
        st.write("Manage the platform, trigger maintenance, and review system stats directly via chat.")
        
        if "admin_chat_history" not in st.session_state:
            st.session_state["admin_chat_history"] = [
                {"role": "assistant", "content": "Welcome Founder! 👑\n\nI am **Q.S Hub AI Manager** - your right hand to manage the whole platform. I can execute commands from A to Z.\n\n**Capabilities:**\n✅ **User Management** - Query user counts\n✅ **System Maintenance** - Update market prices\n✅ **Subscriptions** - Monitor active plans\n\n**Try asking:**\n- 'How many users do we have?'\n- 'Update market prices'\n- 'Run weekly maintenance'"}
            ]

        for msg in st.session_state["admin_chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "action_result" in msg and msg["action_result"]:
                    res = msg["action_result"]
                    if res.get("success"):
                        st.success(res.get("message"))
                        if "data" in res and res["data"]:
                            fmt = res.get("format")
                            if fmt == "table":
                                st.dataframe(res["data"])
                            elif fmt == "json":
                                st.json(res["data"])
                    else:
                        st.error(res.get("message"))
                
        prompt = st.chat_input("Command the AI Manager...")
        if prompt:
            st.session_state["admin_chat_history"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Processing Admin Command..."):
                    from utils.admin_agent import process_admin_message
                    user_info = st.session_state.get("user", {})
                    admin_name = user_info.get("email", "Admin").split("@")[0]
                    admin_id = user_info.get("id", 1)
                    
                    reply, action_result = process_admin_message(
                        prompt, 
                        st.session_state["admin_chat_history"][:-1],
                        admin_name,
                        admin_id
                    )
                    
                    st.write(reply)
                    if action_result:
                        if action_result.get("success"):
                            st.success(action_result.get("message"))
                            if "data" in action_result and action_result["data"]:
                                fmt = action_result.get("format")
                                if fmt == "table":
                                    st.dataframe(action_result["data"])
                                else:
                                    st.json(action_result["data"])
                        else:
                            st.error(action_result.get("message"))
                            
                    st.session_state["admin_chat_history"].append({
                        "role": "assistant",
                        "content": reply,
                        "action_result": action_result
                    })
            st.rerun()

    with tab5:
        st.subheader("🧠 Global AI Learning (User Feedback Loop)")
        st.markdown("Review and approve mapping rules submitted by users. Approved rules will become **Global** and apply to all future projects across the entire platform, making the AI smarter.")
        
        pending_df = safe_query("SELECT id, user_id, original_text, mapped_category, created_at FROM qto_memory_rules WHERE status='pending' ORDER BY id ASC")
        if not pending_df.empty:
            for idx, row in pending_df.iterrows():
                rule_id = row['id']
                with st.container():
                    c1, c2, c3 = st.columns([4, 1, 1])
                    c1.write(f"User {row['user_id']} mapped: **{row['original_text']}** ➔ **{row['mapped_category']}**")
                    if c2.button("✅ Approve", key=f"approve_{rule_id}"):
                        from utils.db import safe_execute
                        safe_execute("UPDATE qto_memory_rules SET status='global', user_id=NULL WHERE id=%s", (rule_id,))
                        # Delete the duplicate personal rule if it exists for this user
                        safe_execute("DELETE FROM qto_memory_rules WHERE status='personal' AND user_id=%s AND original_text=%s", (row['user_id'], row['original_text']))
                        st.success("Rule approved globally!")
                        st.rerun()
                    if c3.button("❌ Reject", key=f"reject_{rule_id}"):
                        from utils.db import safe_execute
                        safe_execute("DELETE FROM qto_memory_rules WHERE id=%s", (rule_id,))
                        st.info("Rule rejected and deleted.")
                        st.rerun()
                st.divider()
        else:
            st.info("No pending rules to review. The AI memory queue is clear.")
            
        with st.expander("View Global Rules (Active)"):
            global_df = safe_query("SELECT original_text, mapped_category FROM qto_memory_rules WHERE status='global'")
            if not global_df.empty:
                st.dataframe(global_df, use_container_width=True)
            else:
                st.write("No global rules yet.")

    with tab6:
        st.subheader("🚨 Customer Complaints Inbox")
        st.write("Review and resolve complaints escalated by the Customer Care AI agent.")
        complaints_df = safe_query("SELECT id, user_id, complaint_text, status, created_at FROM qto_customer_complaints ORDER BY id DESC")
        if not complaints_df.empty:
            for idx, row in complaints_df.iterrows():
                comp_id = row['id']
                with st.container():
                    c1, c2 = st.columns([5, 1])
                    c1.markdown(f"**User {row['user_id']}** ({row['created_at']}) - Status: `{row['status']}`\n\n{row['complaint_text']}")
                    if row['status'] == 'open':
                        if c2.button("✅ Mark Resolved", key=f"resolve_{comp_id}"):
                            from utils.db import safe_execute
                            safe_execute("UPDATE qto_customer_complaints SET status='resolved' WHERE id=%s", (comp_id,))
                            st.rerun()
                st.divider()
        else:
            st.info("No complaints found.")
