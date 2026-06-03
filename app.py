import os
import streamlit as st

# ── RENDER PROXY MODE ──
# If running on Render, serve the high-speed HuggingFace Space via an iframe.
# This allows keeping the custom domain (qshub.online) while using 16GB RAM for processing!
if os.environ.get("RENDER") == "true" or os.environ.get("RENDER") == "1" or "RENDER" in os.environ:
    st.set_page_config(page_title="THE QS HUB", page_icon="ui/logo.png", layout="wide")
    st.markdown("""
        <style>
            [data-testid="stAppViewContainer"], .stApp { margin: 0 !important; padding: 0 !important; }
            iframe { width: 100vw; height: 100vh; border: none; position: fixed; top: 0; left: 0; z-index: 999999; }
            [data-testid="stHeader"], footer, [data-testid="stSidebar"] { display: none !important; }
        </style>
        <iframe src="https://basel0-qshub.hf.space/?embed=true"></iframe>
    """, unsafe_allow_html=True)
    st.stop()

st.set_page_config(
    page_title="THE QS HUB",
    page_icon="ui/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dotenv import load_dotenv
load_dotenv()

from utils.observability import init_observability
from datetime import datetime, timedelta
from ui.page_market_prices import auto_daily_update

init_observability()

# Auto daily update background task (Lazy Cron)
auto_daily_update()

# ── Password Reset Flow ──
if "reset_token" in st.query_params:
    st.markdown("<h2 style='text-align:center;'>Reset Your Password</h2>", unsafe_allow_html=True)
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    if st.button("Update Password", type="primary", use_container_width=True):
        if len(new_password) < 6:
            st.error("Password must be at least 6 characters.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            from utils.security import reset_password_with_token
            if reset_password_with_token(st.query_params["reset_token"], new_password):
                st.success("Password updated successfully! You can now log in.")
                st.query_params.clear()
                import time; time.sleep(2); st.rerun()
            else:
                st.error("Invalid or expired reset token.")
    st.stop()  # Stop rendering the rest of the app

# ── Session state defaults ──
_defaults = {
    "current_step": 1,
    "project_name": f"Villa Project {datetime.now().strftime('%m-%d %H:%M')}",
    "num_floors": 2,
    "gf_height": 4.0, "f1_height": 4.0, "f2_height": 4.0,
    "excavation_depth": 1.25,
    "include_road_base": True,
    "str_pages": [], "arch_pages": [],
    "str_texts": [], "arch_texts": [],
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def show_terms_dialog():
    from utils.i18n import get_lang
    ar = (get_lang() == "ar")
    if ar:
        st.markdown("""
        ### شروط الاستخدام لمنصة THE QS HUB
        **تاريخ التحديث:** مايو 2026
        
        مرحباً بكم في منصة **THE QS HUB**. باستخدامكم لهذا التطبيق، فإنكم توافقون على الشروط والأحكام التالية:
        
        #### 1. الخدمات المقدمة
        يوفر التطبيق أداة حساب كميات (QTO) مؤتمتة للمشاريع والفلل السكنية باستخدام تقنيات الرؤية الحاسوبية والذكاء الاصطناعي.
        
        #### 2. مسؤولية الحصر والمراجعة الهندسية
        * **تنبيه هام:** المخرجات والكميات الناتجة هي قيم إرشادية وحسابات آلية تهدف إلى تسريع الحصر وتوفير الوقت بنسبة 80%.
        * **مسؤولية المقدر:** يتحمل المقدر أو المهندس المسؤول عن المشروع كامل المسؤولية لمراجعة وتدقيق الكميات هندسياً وتأكيدها قبل اتخاذ أي قرارات تعاقدية أو تقديم عطاءات أسعار.
        * لا يتحمل مطورو النظام أي مسؤولية مادية أو قانونية عن أي تفاوت في الكميات أو أخطاء ناتجة عن عدم المراجعة البشرية الدقيقة.
        
        #### 3. الملكية الفكرية للمخططات
        تظل كافة المخططات وملفات الـ PDF المرفوعة ملكاً كاملاً للمستخدم. ولا يحق للمنصة استخدامها تجارياً أو نشرها لأطراف ثالثة.
        
        #### 4. الحسابات والاشتراكات
        * يمنع مشاركة حسابات الدخول والاشتراكات مع مستخدمين آخرين خارج المؤسسة المصرح لها.
        * يتم إدارة جميع الفواتير والاشتراكات بشكل آمن ومستقل تماماً.
        """)
    else:
        st.markdown("""
        ### Terms of Use for THE QS HUB
        **Last Updated:** May 2026
        
        Welcome to **THE QS HUB**. By accessing and using this application, you agree to comply with the following terms:
        
        #### 1. Services Provided
        The platform provides automated Quantity Takeoff (QTO) software for residential villa projects using computer vision and AI technologies.
        
        #### 2. Engineering Verification Responsibility
        * **Important Notice:** The calculated quantities are indicative approximations designed to save up to 80% of manual estimation time.
        * **Estimator Responsibility:** The user/engineer retains full and final responsibility to inspect, review, verify, and approve all quantities before submitting tenders or signing contracts.
        * The developers of the system shall not be held liable for any direct or indirect financial losses arising from discrepancies in automated takeoffs.
        
        #### 3. Blueprint IP Intellectual Property
        All blueprints and PDF files uploaded remain the exclusive property of the user. The platform will not use, share, or sell these blueprints.
        
        #### 4. User Accounts & Subscriptions
        * Sharing user accounts or subscriptions outside the licensed organization is strictly prohibited.
        """)

def show_privacy_dialog():
    from utils.i18n import get_lang
    ar = (get_lang() == "ar")
    if ar:
        st.markdown("""
        ### سياسة الخصوصية وحماية بيانات المخططات والمعلومات الهندسية
        **تاريخ التحديث:** مايو 2026
        
        نحن في **THE QS HUB** ملتزمون بحماية البيانات الهندسية والمخططات الفنية الخاصة بكم بأعلى معايير الأمان المتبعة دولياً.
        
        #### 1. جمع البيانات والمخططات وحمايتها
        * يتم معالجة المخططات التي ترفعونها بصيغة PDF بشكل آمن لغرض استخراج جداول الكميات فقط.
        * يتم تصفح المخططات من خلال قنوات مشفرة آمنة (HTTPS / SSL).
        * يتم تخزين استجابات الذكاء الاصطناعي للمخططات بشكل مؤقت في خادم آمن وتجريدها من أي بيانات حساسة تخص العميل النهائي.
        
        #### 2. أمن الخادم وقاعدة البيانات
        * يتم استضافة قاعدة البيانات على خوادم **TiDB Cloud MySQL** المشفرة بالكامل.
        * نتبع سياسة صارمة لمنع الوصول غير المصرح به لملفات ومجلدات التخزين المؤقت المشفرة للنتائج.
        
        #### 3. عدم مشاركة البيانات مع جهات خارجية
        لا نقوم مطلقاً ببيع أو تأجير أو مشاركة مخططاتكم الهندسية أو معلومات مشاريعكم مع أي أطراف ثالثة أو شركات منافسة. يتم توجيه طلبات الفحص عبر قنوات API مشفرة وآمنة ومحمية بموجب شروط حماية البيانات للمؤسسات (Enterprise Data Protection Terms).
        """)
    else:
        st.markdown("""
        ### Privacy & Data Protection Policy
        **Last Updated:** May 2026
        
        At **THE QS HUB**, we are deeply committed to protecting your technical engineering data and blueprints using industry-standard security protocols.
        
        #### 1. Technical Data & Blueprint Protection
        * All uploaded PDF blueprints are processed securely for the sole purpose of extracting takeoff quantities.
        * Blueprint viewing and transfer occur exclusively over encrypted channels (HTTPS / SSL).
        * Cached AI responses are stored in encrypted databases to ensure client confidentiality.
        
        #### 2. Server & Data Security
        * The live database is hosted on **TiDB Cloud MySQL** with full SSL encryption.
        * Rigid directory-level policies restrict access to cached files in secure directories.
        
        #### 3. Third-Party Sharing Policies
        We strictly do not share, sell, or rent your blueprint files or project metadata to third parties. All AI extraction requests are processed through secure enterprise channels protected by Enterprise Data Protection Terms.
        """)

# ── Imports ──
from workflow.workflow_state import STEPS, get_current_step, set_step, step_done
from workflow.step1_upload    import render_step1
from workflow.step2_classify  import render_step2
from workflow.step3_extract   import render_step3
from workflow.step4_confirm   import render_step4
from workflow.step5_calculate import render_step5
from workflow.step6_review    import render_step6
from workflow.step7_arrange   import render_step7
from workflow.step8_download  import render_step8
from ui.site_pages import render_home, render_projects, render_profile
from utils.i18n import t, get_lang, set_lang, apply_rtl_css, is_rtl

def _apply_theme(dark: bool):
    """In-app light/dark theme toggle with safe modern UI/UX enhancements."""
    font_url = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@300;400;600;800&display=swap"
    icons_url = "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    
    if dark:
        css = f"""
        <style>
        @import url('{font_url}');
        @import url('{icons_url}');
        .material-symbols-outlined {{
            font-family: 'Material Symbols Outlined';
            font-weight: normal; font-style: normal; font-size: 20px; line-height: 1;
            letter-spacing: normal; text-transform: none; display: inline-block;
            white-space: nowrap; word-wrap: normal; direction: ltr;
            -webkit-font-smoothing: antialiased; vertical-align: middle;
        }}
        html, body, [data-testid="stAppViewContainer"] {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}
        footer {{ visibility: hidden; }}
        
        /* Subtle FAB Support Button */
        .support-fab-anchor {{
            display: none;
        }}
        [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div {{
            position: fixed !important;
            bottom: 30px !important;
            right: 30px !important;
            z-index: 999999 !important;
            width: auto !important;
        }}
        [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div button {{
            background: linear-gradient(135deg, #3B82F6, #2563eb) !important;
            color: white !important;
            border-radius: 50% !important;
            width: 65px !important;
            height: 65px !important;
            font-size: 32px !important;
            padding: 0 !important;
            box-shadow: 0 8px 24px rgba(37, 99, 235, 0.5) !important;
            border: 2px solid rgba(255,255,255,0.1) !important;
            transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div button:hover {{
            transform: scale(1.08) translateY(-4px) !important;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.6) !important;
        }}
        </style>"""
    else:
        css = f"""
        <style>
        @import url('{font_url}');
        @import url('{icons_url}');
        .material-symbols-outlined {{
            font-family: 'Material Symbols Outlined';
            font-weight: normal; font-style: normal; font-size: 20px; line-height: 1;
            letter-spacing: normal; text-transform: none; display: inline-block;
            white-space: nowrap; word-wrap: normal; direction: ltr;
            -webkit-font-smoothing: antialiased; vertical-align: middle;
        }}
        :root {{
            --secondary-background-color: #F8FAFC;
            --border-color: #E2E8F0;
            --primary-glow: rgba(59, 130, 246, 0.3);
            --text-main: #0F172A;
            --text-muted: #64748B;
        }}
        
        /* Subtle FAB Support Button */
        .support-fab-anchor {{
            display: none;
        }}
        [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div {{
            position: fixed !important;
            bottom: 30px !important;
            right: 30px !important;
            z-index: 999999 !important;
            width: auto !important;
        }}
        [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div button {{
            background: linear-gradient(135deg, #3B82F6, #2563eb) !important;
            color: white !important;
            border-radius: 50% !important;
            width: 65px !important;
            height: 65px !important;
            font-size: 32px !important;
            padding: 0 !important;
            box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4) !important;
            border: 2px solid rgba(255,255,255,0.8) !important;
            transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div button:hover {{
            transform: scale(1.08) translateY(-4px) !important;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.5) !important;
        }}

        html, body, [data-testid="stAppViewContainer"] {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}
        
        [data-testid="stAppViewContainer"], .main {{ background: #F1F5F9 !important; color: var(--text-main) !important; }}
        [data-testid="stSidebar"] {{ 
            background: rgba(255, 255, 255, 0.8) !important; 
            border-right: 1px solid rgba(0,0,0,0.05) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
        }}
        [data-testid="stHeader"] {{ background: rgba(241, 245, 249, 0.6) !important; backdrop-filter: blur(12px) !important; }}
        
        /* Typography */
        h1:not(.hero-title), h2, h3, h4, h5, h6, label, small, .stText {{ color: var(--text-main) !important; }}
        [data-testid="stMarkdownContainer"] > p, [data-testid="stMarkdownContainer"] > ul > li {{ color: var(--text-main) !important; }}
        /* Protect Alerts and Buttons */
        [data-testid="stAlert"] * {{ color: inherit !important; }}
        .stButton > button * {{ color: white !important; }}
        .stCaption div {{ color: var(--text-muted) !important; }}
        
        /* Inputs & Dropdowns */
        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {{
            background: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: var(--text-main) !important;
            border-radius: 12px !important;
            padding: 10px 14px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        }}
        .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus-within {{
            border-color: #3B82F6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
        }}
        
        /* Buttons */
        .stButton>button {{
            background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 6px 20px !important;
            font-weight: 600 !important;
            letter-spacing: 0.3px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        }}
        .stButton>button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4) !important;
            background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        }}
        
        /* Sidebar Specific Buttons */
        [data-testid="stSidebar"] button {{
            background: transparent !important;
            color: var(--text-muted) !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
            border-radius: 8px !important;
            padding: 6px 8px !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            box-shadow: none !important;
            text-align: center !important;
            white-space: normal !important;
            word-break: break-word !important;
            min-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}
        [data-testid="stSidebar"] button * {{
            color: inherit !important;
        }}
        [data-testid="stSidebar"] button:hover {{
            color: var(--text-main) !important;
            border-color: #3B82F6 !important;
            background: rgba(59, 130, 246, 0.05) !important;
            transform: none !important;
        }}
        
        /* File Uploader */
        [data-testid="stFileUploaderDropzone"] {{
            background: #FFFFFF !important;
            border: 2px dashed #CBD5E1 !important;
            border-radius: 16px !important;
            padding: 30px 20px !important;
            transition: all 0.3s ease !important;
        }}
        [data-testid="stFileUploaderDropzone"]:hover {{
            border-color: #3b82f6 !important;
            background: #F8FAFC !important;
            transform: scale(1.01) !important;
        }}
        [data-testid="stFileUploaderDropzone"] button {{
            background: #F1F5F9 !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            color: #0F172A !important;
        }}
        [data-testid="stFileUploaderDropzone"] span, 
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] div {{
            color: #64748B !important;
        }}
        
        /* Force Chat & Modals to Light Theme */
        div[role="dialog"], 
        [data-testid="stChatInput"], 
        [data-testid="stChatInput"] textarea, 
        [data-testid="stChatMessage"] {{
            background-color: #FFFFFF !important;
            color: #0F172A !important;
        }}
        div[role="dialog"] * {{
            color: #0F172A !important;
            fill: #0F172A !important;
        }}
        div[role="dialog"], [data-testid="stChatInput"], [data-testid="stChatMessage"] {{
            border: 1px solid #CBD5E1 !important;
            border-radius: 12px !important;
        }}
        
        /* Expanders and Dividers */
        [data-testid="stExpander"] {{
            border: 1px solid #CBD5E1 !important;
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
        }}
        hr {{
            border: none !important;
            height: 2px !important;
            background-color: #CBD5E1 !important;
            margin: 20px 0 !important;
        }}
        
        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(0,0,0,0.1); border-radius: 10px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(0,0,0,0.2); }}
        /* Custom Tables */
        .styled-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 0.9em; min-width: 400px; color: var(--text-main); }}
        .styled-table thead tr {{ background-color: rgba(59,130,246,0.1); text-align: left; border-bottom: 2px solid rgba(59,130,246,0.4); }}
        .styled-table th, .styled-table td {{ padding: 12px 15px; border-bottom: 1px solid rgba(0,0,0,0.05); }}
        .styled-table tbody tr:nth-of-type(even) {{ background-color: rgba(0,0,0,0.02); }}
        
        footer {{ visibility: hidden; }}
        </style>"""
    
    st.markdown(css, unsafe_allow_html=True)




# ── The Analysis page = the 8-step workflow ──────────────────────────────────
def render_analysis():
    col_title, col_proj, col_new = st.columns([2, 1, 1])
    with col_title:
        st.markdown(t("analysis_title"))
    with col_proj:
        st.session_state["project_name"] = st.text_input(
            t("project_name"), value=st.session_state.get("project_name", "Villa Project"), label_visibility="collapsed")
    with col_new:
        if st.button("🆕 New Project" if get_lang()=="en" else "🆕 مشروع جديد", use_container_width=True):
            keys_to_clear = ["current_step", "project_id", "project_name", "str_pages", "arch_pages", "str_texts", "arch_texts", 
                             "classified_pages", "extraction_results", "quantities", "step_done"]
            for k in list(st.session_state.keys()):
                if k in keys_to_clear or k.startswith("nav_") or k.endswith("_done"):
                    del st.session_state[k]
            import glob, os
            for f in glob.glob("_*_data.json"):
                try: os.remove(f)
                except: pass
            st.rerun()

    st.divider()

    # Material icon name for each step (professional, minimal)
    STEP_ICONS = {
        1: "upload_file",
        2: "category",
        3: "query_stats",
        4: "fact_check",
        5: "calculate",
        6: "preview",
        7: "reorder",
        8: "download",
    }

    current = get_current_step()
    step_cols = st.columns(8)
    for i, (num, info) in enumerate(STEPS.items()):
        with step_cols[i]:
            done   = step_done(info["key"])
            active = (num == current)
            
            bg = "linear-gradient(135deg, #3b82f6, #2563eb)" if active else ("rgba(16, 185, 129, 0.1)" if done else "var(--secondary-background-color)")
            color = "white" if active else ("#10b981" if done else "inherit")
            border = "none" if active else ("1px solid rgba(16, 185, 129, 0.3)" if done else "1px solid rgba(128,128,128,0.2)")
            shadow = "0 10px 15px -3px rgba(59, 130, 246, 0.3)" if active else "none"
            transform = "scale(1.05) translateY(-2px)" if active else "scale(1)"
            icon_color = "white" if active else ("#10b981" if done else "#64748b")
            icon_name = STEP_ICONS.get(num, "")
                
            style = f"""
                background: {bg};
                color: {color};
                border: {border};
                padding: 10px 4px;
                border-radius: 12px;
                text-align: center;
                box-shadow: {shadow};
                transform: {transform};
                transition: all 0.3s ease;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 4px;
                min-height: 62px;
                margin-bottom: 8px;
                cursor: default;
            """
            
            label = info["label_ar"] if is_rtl() else info["label"]
            icon_html = f'<span class="material-symbols-outlined" style="font-size:24px;color:{icon_color};">{icon_name}</span>' if icon_name else ''
            st.markdown(f'<div style="{style}">{icon_html}<small style="font-weight:600;line-height:1.2;white-space:normal;">{label}</small></div>',
                        unsafe_allow_html=True)
            if done and num != current:
                if st.button(t("step_nav_go"), key=f"nav_{num}", use_container_width=True):
                    set_step(num)
                    st.rerun()

    st.divider()

    renderers = {1: render_step1, 2: render_step2, 3: render_step3, 4: render_step4,
                 5: render_step5, 6: render_step6, 7: render_step7, 8: render_step8}
    renderer = renderers.get(current)
    if renderer:
        proceeded = renderer()
        if proceeded and current < 8:
            set_step(current + 1)
            st.rerun()


from ui.page_landing import render_landing
from ui.page_auth import render_auth
from ui.page_market_prices import render_market_prices
from ui.page_ai_agents import render_ai_agents

is_logged_in = st.session_state.get("user") is not None

if is_logged_in:
    if "session_started_at" not in st.session_state:
        st.session_state["session_started_at"] = datetime.utcnow().isoformat()
    try:
        started = datetime.fromisoformat(st.session_state["session_started_at"])
        if datetime.utcnow() - started > timedelta(hours=8):
            del st.session_state["user"]
            st.warning("Session expired. Please sign in again.")
            st.rerun()
    except Exception:
        st.session_state["session_started_at"] = datetime.utcnow().isoformat()

if is_logged_in:
    if st.session_state["user"].get("role") == "blocked":
        del st.session_state["user"]
        if "nav_page" in st.session_state:
            del st.session_state["nav_page"]
        st.rerun()
    
    from utils.plans import get_plan_for_user
    user_plan = get_plan_for_user(st.session_state["user"]["id"], st.session_state["user"].get("role"))
    
    # Base pages available to all logged-in users
    PAGES = ["home", "analysis", "comparison", "projects", "market", "agents", "billing", "legal", "profile"]
        
    if st.session_state["user"].get("role") == "admin":
        PAGES.append("admin")
else:
    PAGES = ["landing", "auth"]

if "nav_page" not in st.session_state or st.session_state["nav_page"] not in PAGES:
    st.session_state["nav_page"] = PAGES[0]

if "_goto" in st.session_state:
    target = st.session_state["_goto"].lower()
    if target in PAGES:
        st.session_state["nav_page"] = target
    del st.session_state["_goto"]

# Handle URL query params for Paddle bots (?page=billing, ?page=legal)
qp = st.query_params.get("page")
if qp:
    q = qp.lower()
    # If the user is not logged in, "billing" and "legal" are not in PAGES by default,
    # so we temporarily append them just to allow viewing the public versions of those pages!
    if q in ["billing", "legal"] and q not in PAGES:
        PAGES.append(q)
    if q in PAGES:
        st.session_state["nav_page"] = q
        st.query_params.clear()

with st.sidebar:
    # ── Logo / Brand ──
    import base64
    import os
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "ui", "logo.png")
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width:56px;height:56px;border-radius:12px;object-fit:cover;"/>'
    except Exception:
        logo_html = '<div style="background:linear-gradient(135deg,#2563eb,#1d4ed8);border-radius:12px;width:56px;height:56px;display:flex;align-items:center;justify-content:center;flex-shrink:0;"><span class="material-symbols-outlined" style="color:white;font-size:32px;">architecture</span></div>'

    st.markdown(
        f"""<div style="padding:12px 16px 4px;">
          <div style="display:flex;align-items:center;gap:10px;">
            {logo_html}
            <div>
              <div class="logo-title" style="font-size:1.3rem;font-weight:800;line-height:1.1;color:var(--text-main) !important;">THE QS HUB</div>
            </div>
          </div>
        </div>""",
        unsafe_allow_html=True
    )

    st.divider()

    # ── Language Toggle ──
    current_lang = get_lang()
    new_lang = st.radio(
        "Language",
        ["English", "العربية"],
        index=0 if current_lang == "en" else 1,
        horizontal=True,
        label_visibility="collapsed"
    )
    if (new_lang == "العربية" and current_lang != "ar") or (new_lang == "English" and current_lang != "en"):
        set_lang("ar" if new_lang == "العربية" else "en")
        st.rerun()

    st.divider()

    # ── Navigation ──
    st.markdown(
        f"<div style='font-size:0.7rem;font-weight:700;color:#94a3b8;text-transform:uppercase;"
        f"letter-spacing:0.1em;padding:0 4px 8px;'>{t('nav_label')}</div>",
        unsafe_allow_html=True
    )
    
    def get_page_label(p):
        if p == "landing":
            return "Home" if get_lang() == "en" else "الرئيسية"
        elif p == "auth":
            return "Auth" if get_lang() == "en" else "تسجيل الدخول"
        else:
            return t(f"nav_{p}")

    page = st.radio(
        "Navigation",
        PAGES,
        format_func=get_page_label,
        key="nav_page",
        label_visibility="collapsed"
    )
    
    if is_logged_in:
        st.divider()
        st.markdown(f"<div style='font-size:0.8rem; color:#64748b; padding:0 4px;'>{t('logged_in_as')} <b>{st.session_state['user'].get('email')}</b></div>", unsafe_allow_html=True)
        if st.button(t("logout_btn"), use_container_width=True):
            del st.session_state["user"]
            # Clear nav_page so app.py resets it to Landing on next run
            if "nav_page" in st.session_state:
                del st.session_state["nav_page"]
            st.rerun()

    st.divider()

    # ── Theme ──
    st.markdown(
        f"<div style='font-size:0.7rem;font-weight:700;color:#94a3b8;text-transform:uppercase;"
        f"letter-spacing:0.1em;padding:0 4px 8px;'>{t('theme_label')}</div>",
        unsafe_allow_html=True
    )
    
    is_dark = st.session_state.get("is_dark_theme", True)
    is_dark = st.toggle(
        "🌙 Dark Mode" if current_lang == "en" else "🌙 الوضع الداكن",
        value=is_dark,
        key="ui_theme_toggle"
    )
    st.session_state["is_dark_theme"] = is_dark
    theme_val = "dark" if is_dark else "light"

    st.divider()
    # ── Policy & Legal Links ──
    terms_lbl = "📄 شروط الاستخدام" if current_lang == "ar" else "📄 Terms of Use"
    privacy_lbl = "🔒 سياسة الخصوصية" if current_lang == "ar" else "🔒 Privacy Policy"
    
    with st.expander(terms_lbl):
        show_terms_dialog()
    with st.expander(privacy_lbl):
        show_privacy_dialog()



_apply_theme(dark=theme_val == "dark")
apply_rtl_css()

from ui.page_admin import render_admin

# ── Route ──
if not is_logged_in:
    if page == "landing":
        render_landing()
    elif page == "auth":
        render_auth()
    else:
        render_landing()
else:
    if page == "home":
        render_home()
    elif page == "analysis":
        from utils.plans import get_plan_for_user
        if get_plan_for_user(st.session_state["user"]["id"], st.session_state["user"].get("role")).tier == 0:
            st.session_state["_goto"] = "billing"
            st.rerun()
        render_analysis()
    elif page == "comparison":
        from utils.plans import get_plan_for_user
        if get_plan_for_user(st.session_state["user"]["id"], st.session_state["user"].get("role")).tier == 0:
            st.session_state["_goto"] = "billing"
            st.rerun()
        from ui.page_plan_comparison import render_plan_comparison
        render_plan_comparison()
    elif page == "projects":
        render_projects()
    elif page == "market":
        render_market_prices()
    elif page == "agents":
        from utils.plans import get_plan_for_user
        if get_plan_for_user(st.session_state["user"]["id"], st.session_state["user"].get("role")).tier == 0:
            st.session_state["_goto"] = "billing"
            st.rerun()
        render_ai_agents()
    elif page == "billing":
        from ui.page_billing import render_billing
        render_billing()
    elif page == "legal":
        from ui.page_legal import render_legal
        render_legal()
    elif page == "profile":
        render_profile()
    elif page == "admin":
        render_admin()

# ── Customer Support FAB (Floating Action Button) ──
if is_logged_in:
    ar = (get_lang() == "ar")
    st.markdown('<div class="support-fab-anchor"></div>', unsafe_allow_html=True)
    with st.popover("💬", use_container_width=False):
        st.markdown("<h3 style='margin-bottom:0;'>🎧 Customer Support</h3>" if not ar else "<h3 style='margin-bottom:0;'>🎧 خدمة العملاء</h3>", unsafe_allow_html=True)
        st.caption("Chat with Sarah..." if not ar else "تحدث مع سارة...")
        
        user = st.session_state["user"]
        welcome_cc = "أهلاً بك باشمهندس باسل! أنا سارة من فريق خدمة العملاء. كيف يمكنني مساعدتك في حسابك أو الباقات؟" if ar else "Welcome Eng. Basel! I am Sarah from Customer Support. How can I assist you with your account or billing?"
        
        if "cc_chat_history" not in st.session_state:
            st.session_state["cc_chat_history"] = [{"role": "assistant", "content": welcome_cc}]
            
        for msg in st.session_state["cc_chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        prompt_cc = st.chat_input("Message Support..." if not ar else "راسل الدعم الفني...", key="input_cc")
        if prompt_cc:
            st.session_state["cc_chat_history"].append({"role": "user", "content": prompt_cc})
            st.rerun() # Re-render to show user message immediately

        # If the last message was from the user, generate response
        if st.session_state["cc_chat_history"][-1]["role"] == "user":
            with st.chat_message("assistant"):
                with st.spinner("Typing..." if not ar else "جاري الكتابة..."):
                    from ui.page_ai_agents import generate_agent_response
                    from utils.audit import check_limit, log_usage, EVENT_AI_CALL
                    ok, msg = check_limit(user, EVENT_AI_CALL)
                    if not ok:
                        st.warning(msg if not ar else "تم الوصول إلى الحد المسموح.")
                    else:
                        log_usage(user["id"], EVENT_AI_CALL, metadata={"role": "cc"})
                        reply = generate_agent_response(st.session_state["cc_chat_history"][-1]["content"], "cc", ar, user["id"])
                        st.session_state["cc_chat_history"].append({"role": "assistant", "content": reply})
                        st.rerun()

# ── Project State Recovery ──
if is_logged_in and page not in ["landing", "auth", "profile", "billing", "legal", "admin", "market", "agents", "comparison", "projects"]:
    # Only show recovery on home/analysis tabs if they are on Step 1
    if st.session_state.get("current_step", 1) == 1:
        from utils.state_recovery import check_has_active_project
        has_active, saved_step, saved_time = check_has_active_project(st.session_state["user"]["id"])
        if has_active:
            if saved_step > 1:
                st.info(f"💾 **Found an unsaved project!** You were on **Step {saved_step}** (Last saved: {saved_time}).")
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("🔄 Resume Project", use_container_width=True):
                        from utils.state_recovery import load_project_state
                        if load_project_state(st.session_state["user"]["id"]):
                            st.success("Project restored! Please re-upload your PDF file if you want to view it.")
                            import time; time.sleep(2); st.rerun()
                with col2:
                    if st.button("🗑️ Start New Project", type="secondary"):
                        from utils.state_recovery import clear_project_state
                        clear_project_state(st.session_state["user"]["id"])
                        st.rerun()

# ── Keep-Alive Component ──
from ui.keep_alive import inject_keep_alive
inject_keep_alive()

# ── Floating Customer Support (FAB) ──
if is_logged_in:
    st.markdown("""
    <style>
    /* Floating Action Button (FAB) CSS targeting the Popover button */
    [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 99999;
    }
    [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div button {
        width: 65px !important;
        height: 65px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
        color: white !important;
        font-size: 32px !important;
        padding: 0 !important;
        box-shadow: 0 8px 24px rgba(37, 99, 235, 0.5) !important;
        border: 2px solid rgba(255,255,255,0.1) !important;
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    [data-testid="stVerticalBlock"] > div:has(.support-fab-anchor) + div button:hover {
        transform: scale(1.08) translateY(-4px) !important;
        box-shadow: 0 12px 28px rgba(37, 99, 235, 0.6) !important;
    }
    /* Constrain the popover content width so it looks like a small chat window */
    div[data-testid="stPopoverBody"] {
        width: 350px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    def render_support_modal():
        from ui.page_ai_agents import generate_agent_response
        from utils.i18n import get_lang
        ar = (get_lang() == "ar")
        
        welcome = "أهلاً بك باشمهندس باسل! أنا مساعد خدمة العملاء. كيف يمكنني مساعدتك؟" if ar else "Welcome Eng. Basel! I am the Support Assistant. How can I assist you?"
        if "cc_chat_history" not in st.session_state:
            st.session_state["cc_chat_history"] = [{"role": "assistant", "content": welcome}]
            
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state["cc_chat_history"]:
                st.chat_message(msg["role"]).write(msg["content"])
                
        prompt = st.chat_input("Message Support..." if not ar else "تحدث مع خدمة العملاء...")
        if prompt:
            st.session_state["cc_chat_history"].append({"role": "user", "content": prompt})
            chat_container.chat_message("user").write(prompt)
            with chat_container.chat_message("assistant"):
                with st.spinner("Thinking..." if not ar else "تكتب الآن..."):
                    reply = generate_agent_response(prompt, "cc", ar)
                    st.write(reply)
                    st.session_state["cc_chat_history"].append({"role": "assistant", "content": reply})
            st.rerun()

    # The anchor that allows CSS to find the popover
    st.markdown("<div class='support-fab-anchor'></div>", unsafe_allow_html=True)
    with st.popover("🎧"):
        render_support_modal()

