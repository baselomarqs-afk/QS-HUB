"""
Site pages: Home (landing), Projects, Profile, Settings.
The Analysis page is the existing 8-step workflow (rendered from app.py).
"""
import os, json, glob
from datetime import datetime
import streamlit as st
from utils.i18n import t

ROOT          = os.path.dirname(os.path.dirname(__file__))
PROFILE_JSON  = os.path.join(ROOT, "_profile.json")
SETTINGS_JSON = os.path.join(ROOT, "_settings.json")
PROJECT_JSON  = os.path.join(ROOT, "_project_data.json")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return {**default, **json.load(f)}
    except Exception:
        return dict(default)


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _goto(page):
    st.session_state["_goto"] = page
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HOME / LANDING
# ══════════════════════════════════════════════════════════════════════════════
def render_home():
    from utils.i18n import is_rtl
    rtl = is_rtl()

    # Hero
    st.markdown(
        f"""
        <div class="custom-hero" style="
            background: linear-gradient(135deg, #0f2057 0%, #1d4ed8 60%, #3b82f6 100%);
            padding: 20px 32px 18px;
            border-radius: 16px;
            color: white;
            text-align: center;
            box-shadow: 0 16px 40px -8px rgba(29,78,216,0.4);
            margin: 4px 0 20px 0;
            position: relative;
            overflow: hidden;
        ">
          <div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px;
               border-radius:50%;background:rgba(255,255,255,0.05);pointer-events:none;"></div>
          <div style="position:relative;z-index:1;">
            <h1 class="hero-title" style="margin:0;color:#ffffff !important;font-size:1.9rem;font-weight:800;
                 letter-spacing:-0.02em;line-height:1.15;">{t('home_title')}</h1>
            <p style="font-size:0.92rem;margin:8px 0 0;color:rgba(255,255,255,0.8) !important;font-weight:300;">
                {t('home_subtitle')}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Stat Cards
    c1, c2 = st.columns(2)
    stats = [
        (c1, "upload_file", "#3b82f6", t("home_new_metric1_val"), t("home_new_metric1_title")),
        (c2, "fact_check",  "#10b981", t("home_new_metric2_val"), t("home_new_metric2_title")),
    ]
    dark = st.session_state.get("ui_theme", "dark") == "dark"
    card_bg = "rgba(255,255,255,0.05)" if dark else "#ffffff"
    card_border = "rgba(255,255,255,0.1)" if dark else "#e2e8f0"
    card_shadow = "0 2px 8px rgba(0,0,0,0.2)" if dark else "0 2px 8px rgba(0,0,0,0.06)"
    card_shadow_hover = "0 8px 24px rgba(0,0,0,0.3)" if dark else "0 8px 24px rgba(0,0,0,0.1)"
    val_color = "#FAFAFA" if dark else "#0f172a"
    label_color = "#94a3b8" if dark else "#64748b"

    for col, icon, color, val, label in stats:
        col.markdown(
            f"""<div style="
                background:{card_bg};
                border:1.5px solid {card_border};
                border-top:3px solid {color};
                border-radius:14px;
                padding:22px 14px 18px;
                text-align:center;
                box-shadow:{card_shadow};
                transition:all 0.25s ease;
            " onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='{card_shadow_hover}'"
              onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='{card_shadow}'">
              <span class="material-symbols-outlined" style="color:{color};font-size:28px;">{icon}</span>
              <div style="font-size:1.8rem;font-weight:800;color:{val_color};line-height:1.1;margin:8px 0 6px;">{val}</div>
              <div style="font-size:0.78rem;font-weight:600;color:{label_color};text-transform:uppercase;letter-spacing:0.08em;">{label}</div>
            </div>""",
            unsafe_allow_html=True
        )

    st.write("")
    st.write("")
    col_btn_l, col_btn_c, col_btn_r = st.columns([1, 2, 1])
    with col_btn_c:
        if st.button(t("home_start_btn"), type="primary", use_container_width=True):
            try:
                from utils.plans import get_plan_for_user
                user_plan = get_plan_for_user(st.session_state["user"]["id"], st.session_state["user"].get("role"))
                if user_plan.tier > 0 or st.session_state["user"].get("role") == "admin":
                    _goto("analysis")
                else:
                    _goto("billing")
            except Exception:
                _goto("billing")

    st.write("")
    st.info(f"⚠️ {t('home_attention')}")

    st.write("")

def render_projects():
    st.title(t('nav_projects'))
    st.divider()
    
    from engine.project_history import load_all_projects
    import pandas as pd
    from utils.exporter import export_boq_to_excel
    
    try:
        user = st.session_state.get("user", {})
        projects = load_all_projects(user.get("id"))
    except Exception as e:
        st.error(f"Database Error: {e}")
        return
        
    if not projects:
        st.info("No projects saved yet. Start a new project to automatically save it here.")
        return
        
    import json
    
    completed_projects = []
    resuming_projects = []
    
    for p in projects:
        boq_data = p.get("boq_data", {})
        if isinstance(boq_data, str):
            try:
                boq_data = json.loads(boq_data)
            except:
                boq_data = {}
        items = boq_data.get("items", [])
        
        if items:
            completed_projects.append((p, items))
        else:
            resuming_projects.append((p, items))
            
    tab1, tab2 = st.tabs(["✅ Completed Projects", "⏳ Resuming Projects (Drafts)"])
    
    def render_resume_button(p, df):
        if st.button(f"▶️ Resume {p['name']} (Step {p.get('current_step', 1)})", key=f"res_{p['id']}_{p['name']}", use_container_width=True, type="primary"):
            # Restore state
            state_data = p.get("state_data", {})
            if isinstance(state_data, str):
                try:
                    state_data = json.loads(state_data)
                except:
                    state_data = {}
            
            for k, v in state_data.items():
                st.session_state[k] = v
                
            st.session_state["project_id"] = p.get("id")
            
            # Reconstruct boq_df if exists
            if df is not None:
                boq_df = df.copy()
                if "_is_header" not in boq_df.columns:
                    boq_df["_is_header"] = False
                st.session_state["boq_df"] = boq_df
            
            # Set routing
            st.session_state["current_step"] = p.get("current_step", 1)
            _goto("analysis")

    with tab1:
        if not completed_projects:
            st.info("You haven't completed any projects yet.")
        for p, items in completed_projects:
            with st.expander(f"🏗️ {p['name']}  |  🕒 {p['date']}"):
                df = pd.DataFrame(items)
                show_df = df.drop(columns=["_is_header"], errors="ignore")
                st.markdown(f'<div style="overflow-x:auto;">{show_df.to_html(classes="styled-table", index=False)}</div>', unsafe_allow_html=True)
                
                excel_bytes = export_boq_to_excel(df, p["name"])
                
                c_dl, c_resume = st.columns(2)
                with c_dl:
                    st.download_button(
                        label=f"⬇️ Download {p['name']} BOQ (Excel)",
                        data=excel_bytes,
                        file_name=f"{p['name']}_BOQ.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_proj_{p['id']}_{p['name']}",
                        use_container_width=True
                    )
                with c_resume:
                    render_resume_button(p, df)

    with tab2:
        if not resuming_projects:
            st.info("You have no pending drafts.")
        for p, items in resuming_projects:
            with st.expander(f"🏗️ {p['name']}  |  🕒 {p['date']} (Step {p.get('current_step', 1)})"):
                st.warning("This project has not reached the final BOQ stage yet.")
                render_resume_button(p, None)
        
# End of render_projects


def render_profile():
    st.markdown(f"<h1 style='color:#3b82f6;'>{t('prof_title')}</h1>", unsafe_allow_html=True)
    prof = _load(PROFILE_JSON, {"name": "", "company": "", "email": "", "role": "QS Engineer"})

    form_style = """
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 32px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    """
    st.markdown(f"<div style='{form_style}'>", unsafe_allow_html=True)
    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        name    = c1.text_input(t("prof_name"), prof["name"])
        company = c2.text_input(t("prof_company"), prof["company"])
        email   = c1.text_input(t("prof_email"), prof["email"])
        role    = c2.selectbox(t("prof_role"),
                               ["QS Engineer", "Estimator", "Project Manager", "Contractor", "Architect"],
                               index=max(0, ["QS Engineer", "Estimator", "Project Manager",
                                             "Contractor", "Architect"].index(prof.get("role", "QS Engineer"))
                                         if prof.get("role") in ["QS Engineer", "Estimator", "Project Manager",
                                                                  "Contractor", "Architect"] else 0))
        st.write("")
        if st.form_submit_button(t("prof_save_btn"), type="primary", use_container_width=True):
            _save(PROFILE_JSON, {"name": name, "company": company, "email": email, "role": role})
            st.success(t("prof_saved"))
    st.markdown("</div>", unsafe_allow_html=True)

    if prof.get("name"):
        st.markdown(f"<div style='text-align:center;opacity:0.7;font-size:1.1em;'> {t('prof_signed_in')} <strong>{prof['name']}</strong>"
                   + (f" · {prof['company']}</div>" if prof.get("company") else "</div>"), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
def render_settings():
    st.markdown("<h1 style='color:#3b82f6;'> Settings | الإعدادات</h1>", unsafe_allow_html=True)
    cfg = _load(SETTINGS_JSON, {
        "currency": "AED", "excavation_depth": 1.25,
        "gf_height": 4.0, "f1_height": 4.0, "f2_height": 4.0,
        "api_keys": [],
    })

    card_style = """
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 32px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    """

    # ── Multi-Key Manager ────────────────────────────────────────────────────
    st.markdown(f"<div style='{card_style}'>", unsafe_allow_html=True)
    st.markdown("### 🔑 AI API Keys | مفاتيح الـ API")
    st.markdown(
        "<div style='background:rgba(59,130,246,0.1); color:#3b82f6; padding:12px; border-radius:8px; margin-bottom:16px;'>"
        " كل مفتاح مجاني يعطيك ~1,500 طلب/يوم (~20 مشروع). "
        "أضف حتى 10 مفاتيح = <strong>150,000 طلب/يوم ≈ 200 مشروع يومياً مجاناً</strong> </div>",
        unsafe_allow_html=True
    )

    # Load saved keys into session state once
    if "api_keys_list" not in st.session_state:
        saved = cfg.get("api_keys", [])
        # Also honour single env key as first entry
        env_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("AI_API_KEY", "")
        if env_key and env_key not in saved:
            saved = [env_key] + saved
        st.session_state["api_keys_list"] = saved or [""]

    keys_in = st.session_state["api_keys_list"]

    # Show one text_input per key slot
    updated_keys = []
    for idx, k in enumerate(keys_in):
        col_k, col_del = st.columns([8, 1])
        val = col_k.text_input(
            f"API Key #{idx + 1}",
            value=k,
            type="password",
            key=f"api_key_slot_{idx}",
            label_visibility="collapsed",
            placeholder=f"Paste API Key #{idx + 1} here…",
        )
        updated_keys.append(val.strip())
        if col_del.button("️", key=f"del_key_{idx}", help="Remove this key"):
            keys_in.pop(idx)
            st.session_state["api_keys_list"] = keys_in
            st.rerun()

    st.write("")
    col_add, col_save = st.columns(2)
    if col_add.button("➕ Add another key | أضف مفتاحاً", use_container_width=True):
        st.session_state["api_keys_list"] = [k for k in updated_keys if k] + [""]
        st.rerun()

    if col_save.button(" Save & Apply Keys | حفظ وتطبيق", type="primary", use_container_width=True):
        clean_keys = [k for k in updated_keys if k]
        st.session_state["api_keys_list"] = clean_keys or [""]
        cfg["api_keys"] = clean_keys
        _save(SETTINGS_JSON, cfg)
        # Apply to the running key manager
        try:
            from utils.key_manager import reload_manager
            reload_manager(clean_keys)
        except Exception:
            pass
        st.success(f" {len(clean_keys)} key(s) saved & active!")

    # Live quota status
    try:
        from utils.key_manager import get_key_manager, reload_manager
        saved_keys = [k for k in updated_keys if k]
        if saved_keys:
            reload_manager(saved_keys)
        mgr = get_key_manager()
        if mgr.key_count() > 0:
            st.divider()
            st.markdown("####  Live Quota Status | حالة الكوتا")
            status = mgr.status()
            for s in status:
                bar_pct = s["remaining"] / 1500
                color = "linear-gradient(90deg, #3b82f6, #10b981)" if s["active"] else ("#475569" if s["exhausted"] else "#1e293b")
                border = "border: 1px solid rgba(59, 130, 246, 0.5);" if s["active"] else "border: 1px solid rgba(255,255,255,0.1);"
                exhausted_txt = " Exhausted" if s["exhausted"] else (" Active" if s["active"] else "⚪ Standby")
                st.markdown(
                    f"<div style='background:rgba(0,0,0,0.2); {border} padding:12px 16px; border-radius:12px; margin:8px 0; display:flex; justify-content:space-between; align-items:center;'>"
                    f"<div><span style='font-family:monospace; opacity:0.8;'> {s['key_hint']}</span> <span style='margin-left:12px; font-weight:600;'>{exhausted_txt}</span></div>"
                    f"<div style='text-align:right;'><strong>{s['remaining']:,}</strong> <span style='opacity:0.6; font-size:0.9em;'>requests left</span></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            total = mgr.total_remaining()
            est_projects = total // 60
            st.markdown(
                f"<div style='background:linear-gradient(135deg, rgba(16,185,129,0.1), rgba(59,130,246,0.1)); border:1px solid rgba(16,185,129,0.2); padding:16px; border-radius:12px; text-align:center; margin-top:16px;'>"
                f"<strong style='font-size:1.1em; color:#10b981;'>مجموع الطلبات المتبقية اليوم: {total:,}</strong><br>"
                f"<span style='opacity:0.8;'>يكفي لـ <strong>~{est_projects} مشروع</strong> إضافي اليوم</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    except Exception:
        pass
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"<div style='{card_style}'>", unsafe_allow_html=True)
    st.markdown("###  Defaults")
    with st.form("settings_form"):
        c1, c2 = st.columns(2)
        currency = c1.selectbox("Currency | العملة", ["AED", "USD", "SAR", "EGP"],
                                index=max(0, ["AED", "USD", "SAR", "EGP"].index(cfg.get("currency", "AED"))))
        exc = c2.number_input("Excavation depth (m)", 0.5, 4.0, float(cfg.get("excavation_depth", 1.25)), 0.05)
        gf  = c1.number_input("GF height (m)", 2.5, 6.0, float(cfg.get("gf_height", 4.0)), 0.1)
        f1  = c2.number_input("1F height (m)", 2.5, 6.0, float(cfg.get("f1_height", 4.0)), 0.1)
        f2  = c1.number_input("2F height (m)", 2.5, 6.0, float(cfg.get("f2_height", 4.0)), 0.1)
        st.write("")
        if st.form_submit_button(" Save settings", type="primary", use_container_width=True):
            new = {**cfg, "currency": currency, "excavation_depth": exc,
                   "gf_height": gf, "f1_height": f1, "f2_height": f2}
            _save(SETTINGS_JSON, new)
            for k, v in new.items():
                if not isinstance(v, (list, dict)):
                    st.session_state[k] = v
            st.success("Settings saved & applied.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### ️ System")
    try:
        from utils.key_manager import get_key_manager
        mgr = get_key_manager()
        st.markdown(
            f"<div style='opacity:0.6; font-size:0.9em; text-align:center;'>"
            f"Model: Proprietary AI Engine &nbsp;•&nbsp; "
            f"API Keys: {mgr.key_count()} active &nbsp;•&nbsp; "
            f"Max capacity: ~{mgr.key_count() * 20} projects/day &nbsp;•&nbsp; "
            f"Reference DB: 35 items / 640 data points"
            f"</div>",
            unsafe_allow_html=True
        )
    except Exception:
        st.markdown("<div style='opacity:0.6; font-size:0.9em; text-align:center;'>Model: Custom AI Model &nbsp;•&nbsp; Reference DB: 35 items / 640 data points</div>", unsafe_allow_html=True)
