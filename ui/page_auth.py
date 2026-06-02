import streamlit as st
import re
from utils.i18n import t
from utils.audit import audit_log
from utils.db import get_connection
from utils.payments import create_checkout_session
from utils.security import (
    issue_reset_token,
    login_rate_limited,
    password_hash,
    password_ok,
    touch_login,
)
from utils.usage import log_usage
from utils.emailer import send_password_reset

def authenticate_user(email, password):
    email = email.strip()
    if login_rate_limited(email):
        st.error("Too many failed login attempts. Please wait 15 minutes.")
        return None
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM qto_users WHERE email=%s", (email,))
                user = cur.fetchone()
        if user and user.get('password_hash'):
            if password_ok(password, user['password_hash']):
                touch_login(user["id"])
                audit_log("login_success", user["id"], "user", user["id"])
                return user
    except Exception as e:
        st.error(f"Database error: {e}")
    log_usage(None, "login_failed", metadata={"email": email})
    return None

def register_user(email, password):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "Invalid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
        
    try:
        hashed_pw = password_hash(password)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM qto_users WHERE email=%s", (email,))
                if cur.fetchone():
                    return False, "Email already exists."
                cur.execute("INSERT INTO qto_users (email, password_hash, role) VALUES (%s, %s, 'user')", (email, hashed_pw))
                user_id = cur.lastrowid
            conn.commit()
        audit_log("user_registered", user_id, "user", user_id, {"email": email})
        return True, "Registration successful! Please login."
    except Exception as e:
        return False, f"Error: {e}"


def plan_tier_from_label(label: str) -> int:
    match = re.search(r"Tier\s+(\d+)", label)
    return int(match.group(1)) if match else 1

def render_auth():
    import os
    import base64
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "logo.png")
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="width:120px;height:120px;border-radius:24px;object-fit:cover;box-shadow:0 8px 24px rgba(0,0,0,0.1);margin-bottom:1rem;"/></div>'
    except Exception:
        logo_html = ""

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(logo_html, unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;'>{t('auth_welcome')}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; color:gray;'>{t('auth_subtitle')}</p>", unsafe_allow_html=True)
        st.write("")
        
        tab_login, tab_signup = st.tabs([t('auth_login_tab'), "Sign Up"])
        
        with tab_login:
            st.write("")
            login_email = st.text_input(
                t("auth_email"), key="login_email",
                placeholder="eng.youremail@example.com"
            )
            login_password = st.text_input(
                t("auth_password"), type="password", key="login_password",
                placeholder="••••••••"
            )
            st.write("")
            if st.button(t("auth_signin_btn"), use_container_width=True, type="primary"):
                with st.spinner("Authenticating..."):
                    user = authenticate_user(login_email, login_password)
                    if user:
                        st.session_state["user"] = user
                        from datetime import datetime
                        st.session_state["session_started_at"] = datetime.utcnow().isoformat()
                        st.success(t("auth_welcome_back"))
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
            
            st.markdown("---")
            with st.expander("Forgot Password?"):
                reset_email = st.text_input("Enter your registered email", key="forgot_email")
                if st.button("Send reset link", use_container_width=True):
                    token = issue_reset_token(reset_email)
                    if token:
                        if send_password_reset(reset_email, token):
                            st.success("Password reset email sent! Check your inbox.")
                        else:
                            st.error("Email service not configured. Please add SMTP_EMAIL and SMTP_PASSWORD to your Render environment variables.")
                            st.info("Temporary token for testing:")
                            st.code(token)
                    else:
                        st.info("If the email exists, a reset link will be sent.")

            st.markdown("---")
            st.markdown("<div style='text-align:center'>Or login with</div>", unsafe_allow_html=True)
            sc1, sc2 = st.columns(2)
            if sc1.button("Google (Coming Soon)", use_container_width=True):
                st.info("Google SSO is being configured.")
            if sc2.button("Microsoft (Coming Soon)", use_container_width=True):
                st.info("Microsoft SSO is being configured.")
                    
        with tab_signup:
            st.write("")
            st.info("Sign up and select your secure subscription plan.")
            st.success("🎉 **SPECIAL OFFER:** 50% OFF your first month on Professional (60 AED) and Business (125 AED) plans!")
            
            reg_email = st.text_input(t("auth_email"), key="reg_email")
            reg_password = st.text_input(t("auth_password"), type="password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            plan = st.selectbox("Select Subscription Plan", [
                "Tier 1: 50 AED / month (1 Project)",
                "Tier 2: 120 AED / month (3 Projects) - 50% OFF 1st Month (60 AED)",
                "Tier 3: 250 AED / month (8 Projects) - 50% OFF 1st Month (125 AED)",
                "Tier 4: 500 AED / month (20 Projects)"
            ])
            
            if st.button("Register & Subscribe", use_container_width=True, type="primary"):
                if reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    success, msg = register_user(reg_email, reg_password)
                    if success:
                        st.success(msg)
                        user = authenticate_user(reg_email, reg_password)
                        if user:
                            st.session_state["user"] = user
                            try:
                                checkout_url = create_checkout_session(user, plan_tier_from_label(plan))
                                st.link_button("Continue to secure checkout", checkout_url, use_container_width=True)
                            except Exception:
                                st.warning("⚠️ **Paddle not configured yet.**\n\n*Preview Mode:* The user will be redirected to the secure payment page here. Once paid, their subscription will automatically activate.")
                    else:
                        st.error(msg)
