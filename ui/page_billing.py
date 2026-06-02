import streamlit as st

from utils.payments import create_checkout_session
from utils.plans import PLANS, get_active_subscription, get_plan_for_user
from utils.usage import monthly_usage, EVENT_AI_CALL, EVENT_EXPORT, EVENT_PROJECT
from utils.settings import get_setting


def render_billing():
    user = st.session_state.get("user")
    
    st.markdown("<h1 style='color:#3b82f6;'>Billing & Subscription</h1>", unsafe_allow_html=True)
    st.caption("Manage plan, usage, Paddle checkout, invoices and account limits.")
    st.divider()

    if user:
        sub = get_active_subscription(user["id"])
        plan = get_plan_for_user(user["id"], user.get("role"))

        c1, c2, c3, c4 = st.columns(4)
        
        # Fetch extra projects
        from utils.db import safe_query
        extra_projects = 0
        try:
            df_extra = safe_query("SELECT extra_projects_allowance FROM qto_users WHERE id=%s", (user["id"],))
            if not df_extra.empty:
                extra_projects = int(df_extra.iloc[0]["extra_projects_allowance"] or 0)
        except Exception:
            pass

        c1.metric("Current Plan", plan.name)
        
        project_limit_str = f"{plan.projects}"
        if extra_projects > 0:
            project_limit_str += f" (+{extra_projects} Add-ons)"
            
        c2.metric("Projects", f"{monthly_usage(user['id'], EVENT_PROJECT)} / {plan.projects + extra_projects}", delta=project_limit_str if extra_projects > 0 else None, delta_color="off")
        
        # Add-on button
        if plan.tier > 0:
            try:
                addon_url = create_checkout_session(user, "addon")
                c2.link_button("Buy Extra Project (+1)", addon_url, use_container_width=True)
            except Exception:
                pass

        if sub:
            st.success(f"Subscription status: {sub.get('status')} | Provider: {sub.get('provider')}")
            if sub.get("current_period_end"):
                st.info(f"Current period ends: {sub.get('current_period_end')}")
        else:
            st.warning("No active subscription found. Choose a plan below.")
        st.divider()
    else:
        st.info("Please sign in or create an account to subscribe to a plan.")
        st.divider()

    st.subheader("Plans")

    cols = st.columns(4)
    for idx, tier in enumerate([1, 2, 3, 4]):
        p = PLANS[tier]
        with cols[idx]:
            price_display = f'<div style="font-size:1.8rem;font-weight:800;">{p.monthly_price_aed} AED</div>'
            badge = ""
            if tier in (2, 3):
                price_display = f'<div style="font-size:1.1rem; text-decoration:line-through; opacity:0.6;">{p.monthly_price_aed} AED</div>'
                price_display += f'<div style="font-size:1.8rem;font-weight:800;color:#10b981;">{p.monthly_price_aed // 2} AED</div>'
                badge = '<div style="position:absolute; top:-12px; right:-12px; background:#ef4444; color:white; font-size:0.75rem; font-weight:bold; padding:4px 12px; border-radius:20px; box-shadow:0 4px 6px rgba(0,0,0,0.1);">🔥 50% OFF (Code: QTO2026)</div>'

            st.markdown(
                f"""
                <div style="position:relative; border:1px solid rgba(128,128,128,0.25);border-radius:12px;padding:18px;min-height:210px;">
                  {badge}
                  <h3 style="margin-top:0;">{p.name}</h3>
                  {price_display}
                  <div style="opacity:.7;margin-bottom:12px;">per month</div>
                  <div style="font-size:1.2rem; margin-top:20px;">Projects: <b>{p.projects}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if user:
                if st.button(f"Choose {p.name}", key=f"choose_plan_{tier}", use_container_width=True):
                    try:
                        url = create_checkout_session(user, tier)
                        st.link_button(f"Subscribe via Paddle Secure Checkout", url, type="primary", use_container_width=True)
                    except Exception:
                        st.warning("⚠️ **Paddle not configured yet.**\n\n*Preview Mode:* Clicking this button will securely redirect the user to the Paddle payment page for this plan.")
            else:
                st.button(f"Sign in to Choose {p.name}", key=f"choose_plan_{tier}", use_container_width=True, disabled=True)

    st.divider()
    portal_url = get_setting("PADDLE_CUSTOMER_PORTAL_URL")
    if portal_url:
        st.link_button("Open Paddle Customer Portal", portal_url, use_container_width=True)
    else:
        st.caption("Set PADDLE_CUSTOMER_PORTAL_URL to expose Paddle self-service portal.")
