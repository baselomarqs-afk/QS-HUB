import streamlit as st
import base64
import os
from utils.i18n import t, get_lang, is_rtl

def get_big_logo():
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "logo.png")
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
        return f'<img src="data:image/png;base64,{logo_b64}" style="width:140px;height:140px;border-radius:24px;object-fit:cover;box-shadow:0 10px 25px rgba(0,0,0,0.2);margin-bottom:20px;"/>'
    except Exception:
        return '<div style="background:linear-gradient(135deg,#2563eb,#1d4ed8);border-radius:24px;width:140px;height:140px;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;box-shadow:0 10px 25px rgba(0,0,0,0.2);"><span class="material-symbols-outlined" style="color:white;font-size:60px;">architecture</span></div>'

def render_landing():
    rtl = is_rtl()
    text_align = "right" if rtl else "center"

    st.markdown(f"""
        <style>
        .hero-container {{
            text-align: center;
            padding: 60px 20px 50px;
            background: linear-gradient(135deg, rgba(37,99,235,0.06) 0%, rgba(59,130,246,0.12) 100%);
            border-radius: 30px;
            margin-bottom: 40px;
            border: 1px solid rgba(59,130,246,0.1);
        }}
        .hero-title {{
            font-size: 3.5rem;
            font-weight: 800;
            color: #3b82f6;
            margin-bottom: 10px;
            line-height: 1.1;
        }}
        .hero-slogan {{
            font-size: 1.2rem;
            color: var(--text-muted);
            margin-bottom: 30px;
        }}
        .feature-card {{
            background: var(--secondary-background-color) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 24px !important;
            padding: 32px 24px !important;
            text-align: center !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: flex-start !important;
        }}
        .feature-card:hover {{
            transform: translateY(-8px) !important;
            box-shadow: 0 20px 30px -10px rgba(59, 130, 246, 0.18) !important;
            border-color: rgba(59, 130, 246, 0.4) !important;
        }}
        .feature-icon-wrapper {{
            width: 60px;
            height: 60px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}
        .feature-card:hover .feature-icon-wrapper {{
            transform: scale(1.1) rotate(4deg);
        }}
        .pricing-card {{
            background: var(--secondary-background-color) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 24px !important;
            padding: 30px 20px !important;
            text-align: center !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            height: 100% !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05) !important;
        }}
        .pricing-card:hover {{
            transform: translateY(-8px) !important;
            box-shadow: 0 20px 30px -10px rgba(59, 130, 246, 0.15) !important;
        }}
        .pricing-tier-label {{ font-size:1rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px; }}
        .pricing-price {{ font-size:2.5rem; font-weight:800; color:var(--text-main); line-height:1; margin-bottom:5px; }}
        .pricing-period {{ font-size:0.9rem; color:var(--text-muted); margin-bottom:20px; }}
        .pricing-feat {{ font-size:0.9rem; color:var(--text-main); margin-bottom:10px; text-align:{"right" if rtl else "left"}; }}
        .extra-text {{ font-size: 0.8rem; color: #94a3b8; margin-top: 20px; }}
        .offer-pill {{ background: rgba(239,68,68,0.1); border: 1px solid #ef4444; color: #ef4444; font-weight: 800; font-size: 0.8rem; padding: 6px 12px; border-radius: 12px; display: inline-block; margin-top: 15px; }}
        </style>
    """, unsafe_allow_html=True)

    # Hero
    st.markdown(f"""
        <div class="hero-container">
            {get_big_logo()}
            <div class="hero-title">{t("app_title")}</div>
            <div class="hero-slogan">{t("landing_slogan")}</div>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        if st.button(t("landing_cta"), use_container_width=True, type="primary"):
            st.session_state["_goto"] = "auth"
            st.rerun()

    st.write("")
    st.write("")

    # Features
    st.markdown(f"<div style='text-align:center;font-size:2rem;font-weight:800;margin-bottom:30px;'>{t('landing_why_title')}</div>", unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown(f"""
        <div class="feature-card">
            <div class="feature-icon-wrapper" style="background: rgba(37,99,235,0.08); color: #3b82f6;">
                <span class="material-symbols-outlined" style="font-size:32px;">flash_on</span>
            </div>
            <h3 style="margin-bottom:12px; font-weight:700;">{t("landing_f1_title")}</h3>
            <p style="color:var(--text-muted); font-size:0.9rem; line-height:1.5; margin:0;">{t("landing_f1_body")}</p>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown(f"""
        <div class="feature-card">
            <div class="feature-icon-wrapper" style="background: rgba(16,185,129,0.08); color: #10b981;">
                <span class="material-symbols-outlined" style="font-size:32px;">smart_toy</span>
            </div>
            <h3 style="margin-bottom:12px; font-weight:700;">{t("landing_f2_title")}</h3>
            <p style="color:var(--text-muted); font-size:0.9rem; line-height:1.5; margin:0;">{t("landing_f2_body")}</p>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown(f"""
        <div class="feature-card">
            <div class="feature-icon-wrapper" style="background: rgba(245,158,11,0.08); color: #f59e0b;">
                <span class="material-symbols-outlined" style="font-size:32px;">trending_up</span>
            </div>
            <h3 style="margin-bottom:12px; font-weight:700;">{t("landing_f3_title")}</h3>
            <p style="color:var(--text-muted); font-size:0.9rem; line-height:1.5; margin:0;">{t("landing_f3_body")}</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")
    st.divider()
    st.write("")

    # Pricing
    st.markdown(f"<div style='text-align:center;font-size:2.5rem;font-weight:800;margin-bottom:40px;'>{t('landing_pricing_title')}</div>", unsafe_allow_html=True)

    extra_text = "(50 درهم لكل مشروع إضافي)" if rtl else "(50 DHS FOR EACH EXTRA PROJECT)"
    offer_text = "خصم 50% لأول شهر! (كود: QTO2026)" if rtl else "50% OFF 1ST MONTH! (CODE: QTO2026)"

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="pricing-tier-label">Tier 1</div>
            <div class="pricing-price">50 <span style="font-size:1rem;">AED</span></div>
            <div class="pricing-period">{t("landing_per_month")}</div>
            <hr style="opacity:0.15;margin-bottom:18px;">
            <div style="font-size:1.2rem; font-weight:bold; color:var(--text-main);">1 Project</div>
        </div>
        """, unsafe_allow_html=True)
    with p2:
        st.markdown(f"""
        <div class="pricing-card" style="border:2px solid #3b82f6; transform:scale(1.02); box-shadow:0 10px 30px rgba(59,130,246,0.2);">
            <div style="background:#3b82f6;color:white;font-size:0.7rem;font-weight:800;padding:4px 10px;border-radius:12px;display:inline-block;margin-bottom:10px;">{t("landing_popular")}</div>
            <div class="pricing-tier-label" style="color:#3b82f6;">Tier 2</div>
            <div class="pricing-price" style="font-size:1.5rem; text-decoration:line-through; opacity:0.6;">120 <span style="font-size:1rem;">AED</span></div>
            <div class="pricing-price" style="color:#10b981;">60 <span style="font-size:1rem;">AED</span></div>
            <div class="pricing-period">{t("landing_per_month")}</div>
            <hr style="opacity:0.15;margin-bottom:18px;">
            <div style="font-size:1.2rem; font-weight:bold; color:var(--text-main);">3 Projects</div>
            <div class="offer-pill">🔥 {offer_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with p3:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="pricing-tier-label">Tier 3</div>
            <div class="pricing-price" style="font-size:1.5rem; text-decoration:line-through; opacity:0.6;">250 <span style="font-size:1rem;">AED</span></div>
            <div class="pricing-price" style="color:#10b981;">125 <span style="font-size:1rem;">AED</span></div>
            <div class="pricing-period">{t("landing_per_month")}</div>
            <hr style="opacity:0.15;margin-bottom:18px;">
            <div style="font-size:1.2rem; font-weight:bold; color:var(--text-main);">8 Projects</div>
            <div class="offer-pill">🔥 {offer_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with p4:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="pricing-tier-label">Tier 4</div>
            <div class="pricing-price">500 <span style="font-size:1rem;">AED</span></div>
            <div class="pricing-period">{t("landing_per_month")}</div>
            <hr style="opacity:0.15;margin-bottom:18px;">
            <div style="font-size:1.2rem; font-weight:bold; color:var(--text-main);">20 Projects</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # --- Footer for Paddle / Public Policy Visibility ---
    st.markdown(f"""
        <div style="text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid var(--border-color);">
            <div style="margin-bottom: 15px;">
                <a href="/?page=billing" style="margin: 0 10px; color: #3b82f6; text-decoration: none; font-weight: 500;">Pricing & Billing</a> | 
                <a href="/?page=legal" style="margin: 0 10px; color: #3b82f6; text-decoration: none; font-weight: 500;">Terms of Service</a> | 
                <a href="/?page=legal" style="margin: 0 10px; color: #3b82f6; text-decoration: none; font-weight: 500;">Privacy Policy</a> | 
                <a href="/?page=legal" style="margin: 0 10px; color: #3b82f6; text-decoration: none; font-weight: 500;">Refund Policy</a>
            </div>
            <p style="color: var(--text-muted); font-size: 0.8rem;">
                © 2026 THE QS HUB. All rights reserved. <br>
                For support, contact us at: support@qshub.online
            </p>
        </div>
    """, unsafe_allow_html=True)
