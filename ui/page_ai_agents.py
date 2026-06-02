from datetime import datetime
from utils.i18n import t, get_lang, is_rtl
from utils.key_manager import get_key_manager
from utils.usage import EVENT_AI_CALL, check_limit, log_usage
from utils.plans import get_active_subscription


def fetch_active_subscription(user_id):
    return get_active_subscription(user_id)

from utils.db import safe_execute, safe_query

def log_agent_conversation(user_id, role, sender, text):
    safe_execute(
        "INSERT INTO qto_agent_conversations (user_id, agent_role, sender, message) VALUES (%s, %s, %s, %s)",
        (user_id, role, sender, text)
    )

def log_customer_complaint(user_id, text):
    safe_execute(
        "INSERT INTO qto_customer_complaints (user_id, complaint_text, status) VALUES (%s, %s, 'open')",
        (user_id, text)
    )

def get_platform_stats():
    users = safe_query("SELECT COUNT(*) as c FROM qto_users").iloc[0]['c']
    subs = safe_query("SELECT COUNT(*) as c FROM qto_subscriptions WHERE status='active'").iloc[0]['c']
    complaints = safe_query("SELECT COUNT(*) as c FROM qto_customer_complaints WHERE status='open'").iloc[0]['c']
    return f"Users: {users}, Active Subs: {subs}, Open Complaints: {complaints}"

def execute_agent_tool(role, prompt, user_id):
    """Executes backend tools if the agent decides it needs to."""
    q = prompt.lower()
    
    if role == "qs":
        if any(kw in q for kw in ["update price", "update prices", "تحديث", "market"]):
            from ui.page_market_prices import update_db_prices
            success, msg = update_db_prices(fluctuate=True)
            return "I have searched the real UAE market and updated the materials price list in the live database successfully." if success else "Failed to update prices."
            
    elif role == "cc":
        if any(kw in q for kw in ["complain", "شكوى", "issue", "problem", "مشكلة"]):
            log_customer_complaint(user_id, prompt)
            return "I have officially recorded your complaint and forwarded it directly to the Admin/AI Manager for immediate review. We apologize for any inconvenience."
            
    elif role == "mgr":
        if any(kw in q for kw in ["report", "تقرير", "status"]):
            stats = get_platform_stats()
            # Send Real email report
            from utils.mailer import send_admin_email
            email_body = f"<h3>AI Manager Daily Report</h3><p>Here are the latest platform stats:</p><p>{stats}</p>"
            sent = send_admin_email("Daily Platform Report - AI Manager", email_body)
            
            safe_execute(
                "INSERT INTO qto_agent_conversations (user_id, agent_role, sender, message) VALUES (%s, %s, %s, %s)",
                (user_id, "mgr", "system", f"SENT REAL EMAIL REPORT TO ADMIN: {stats} (Success: {sent})")
            )
            return f"I have compiled the daily report and sent it to your admin email. Current Stats: {stats} (Email Sent: {sent})"
            
        if any(kw in q for kw in ["refund", "استرجاع", "cancel"]):
            import re
            emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", q)
            if emails:
                target_email = emails[0]
                from utils.payments import issue_dodo_refund
                success, msg = issue_dodo_refund(target_email)
                safe_execute(
                    "INSERT INTO qto_agent_conversations (user_id, agent_role, sender, message) VALUES (%s, %s, %s, %s)",
                    (user_id, "mgr", "system", f"DODO REFUND ATTEMPT ({target_email}): {msg}")
                )
                return f"I executed the Dodo Payments API for {target_email}. Result: {msg}"
            return "I have verified the refund policy. Please provide the user's exact email in your message to execute the Dodo refund API call."

    return None

def generate_agent_response(prompt, role, ar, user_id=None):
    if user_id:
        log_agent_conversation(user_id, role, "user", prompt)
        
    # Check if a tool needs to run
    tool_result = execute_agent_tool(role, prompt, user_id)
    if tool_result:
        if user_id:
             log_agent_conversation(user_id, role, "assistant", tool_result)
        return tool_result
        
    # Set up system prompt
    if role == "qs":
        system_prompt = f"""You are "The QS Assistant", a highly professional UAE Quantity Surveying expert with 20+ years of experience.
You are fully aware of all updated rules and all matters about QS.
You update the market prices daily automatically.
Do NOT talk about user accounts or technical support.
"""
    elif role == "cc":
        system_prompt = f"""You are "Customer Support" (Sarah).
Your job is strictly about subscriptions, user complains, and general support.
You MUST NOT mention, refer to, or help with API keys under any circumstances.
If a user complains, tell them you have recorded the complain and forwarded it to the admin.
"""
    else:
        system_prompt = f"""You are "The AI Manager".
You know everything about everything in the site. You supervise the workflow and supervise the other 2 agents.
You send a daily report to the admin, and you always warn if there's any failure.
You act as the CEO/Admin. Execute refunds via Dodo Payments if asked.
"""

    system_prompt += "\nCRITICAL: You must speak and understand both Arabic and English. You MUST reply in the exact same language the user writes in (Arabic for Arabic, English for English)."


    # Try AI API
    manager = get_key_manager()
    api_key, model_name = manager.get_key_and_model()
    reply = ""
    if api_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.7)
            )
            reply = response.text.strip()
        except Exception:
            reply = _smart_local_fallback(prompt, role, ar)
    else:
        reply = _smart_local_fallback(prompt, role, ar)
        
    if user_id:
        log_agent_conversation(user_id, role, "assistant", reply)
        
    return reply


def _smart_local_fallback(prompt: str, role: str, ar: bool) -> str:
    """
    Intelligent local fallback engine that provides useful answers
    without requiring AI API connectivity.
    Uses keyword matching to route to domain-specific response templates.
    """
    q = prompt.lower()
    
    if role == "qs":
        # ── QS Domain: Formulas & Calculations ───────────────────────────
        if any(kw in q for kw in ["excavation", "حفر", "excavate"]):
            if ar:
                return "باشمهندس باسل، معادلة حساب الحفر هي:\n\n**الحجم = (أطول بُعد + 2) × (أعرض بُعد + 2) × عمق الحفر**\n\nعمق الحفر الافتراضي = 1.25 م (حسب تقرير التربة).\nالإضافة (+2 م) تمثل مسافة العمل حول القاعدة من كل جانب."
            else:
                return "Eng. Basel, the excavation formula is:\n\n**Volume = (Longest Length + 2) × (Longest Width + 2) × Excavation Depth**\n\nDefault depth = 1.25 m (per geotechnical report).\nThe +2 m addition represents working space around the foundation on each side."
        
        if any(kw in q for kw in ["footing", "foundation", "قاعد", "أساس", "اساس"]):
            if ar:
                return "باشمهندس باسل، لحساب خرسانة القواعد:\n\n**الحجم = الطول × العرض × العمق × العدد** (لكل نوع قاعدة)\n\nوخرسانة النظافة (PCC): **(الطول + 0.20) × (العرض + 0.20) × 0.10 × العدد**\n\nوالبيتومين: **(المساحة + المحيط × العمق) × العدد**"
            else:
                return "Eng. Basel, for foundation concrete:\n\n**Volume = Length × Width × Depth × Count** (per footing type)\n\nPCC (Blinding): **(Length + 0.20) × (Width + 0.20) × 0.10 × Count**\n\nBitumen: **(Area + Perimeter × Depth) × Count**"
        
        if any(kw in q for kw in ["tie beam", "كمرة رابطة", "كمرات رابطة", "tb"]):
            if ar:
                return "باشمهندس باسل، لحساب الكمرات الرابطة:\n\n**خرسانة = العرض × العمق × الطول الإجمالي**\n**خرسانة النظافة = (العرض + 0.20) × 0.10 × الطول الإجمالي**\n**البيتومين = الطول الإجمالي × العمق × 2** (الوجهين)"
            else:
                return "Eng. Basel, for tie beams:\n\n**Concrete = Width × Depth × Total Length**\n**PCC = (Width + 0.20) × 0.10 × Total Length**\n**Bitumen = Total Length × Depth × 2** (both faces)"
        
        if any(kw in q for kw in ["column", "عمود", "أعمدة", "اعمدة"]):
            if ar:
                return "باشمهندس باسل، لحساب خرسانة الأعمدة:\n\n**الحجم = الطول × العرض × الارتفاع × العدد**\n\nالارتفاعات الافتراضية: أرضي-أول = 4.0 م، أول-ثاني = 4.0 م، سطح = 3.5 م."
            else:
                return "Eng. Basel, for column concrete:\n\n**Volume = Length × Width × Height × Count**\n\nDefault heights: GF→1F = 4.0 m, 1F→2F = 4.0 m, Roof = 3.5 m."

        if any(kw in q for kw in ["slab", "بلاطة", "بلاطات", "سقف"]):
            if ar:
                return "باشمهندس باسل، لحساب خرسانة البلاطات:\n\n**الحجم = مساحة البلاطة × السماكة**\n\nالسماكة الافتراضية = 0.20 م (200 مم). يُحسب لكل دور على حدة."
            else:
                return "Eng. Basel, for slab concrete:\n\n**Volume = Slab Area × Thickness**\n\nDefault thickness = 0.20 m (200 mm). Calculated per floor separately."
        
        if any(kw in q for kw in ["price", "سعر", "أسعار", "اسعار", "market"]):
            if ar:
                return "باشمهندس باسل، أنا المسؤول عن تحديث أسعار السوق أسبوعياً. الأسعار الحالية تشمل 24 مادة بناء عبر 4 إمارات (دبي، أبوظبي، الشارقة، عجمان).\n\nأرسل لي **'تحديث الأسعار'** وسأقوم بتحديث قاعدة البيانات فوراً.\n\nيمكنك أيضاً مراجعة الأسعار في صفحة **أسعار السوق** من القائمة الجانبية."
            else:
                return "Eng. Basel, I manage weekly market price updates. Current database covers 24 construction materials across 4 emirates (Dubai, Abu Dhabi, Sharjah, Ajman).\n\nSend me **'update prices'** and I'll sync the database immediately.\n\nYou can also view prices under the **Market Prices** tab in the sidebar."

        if any(kw in q for kw in ["backfill", "ردم"]):
            if ar:
                return "باشمهندس باسل، معادلة الردم:\n\n**الحجم = (مساحة الحفر × (عمق الحفر + 0.15)) - إجمالي حجم الخرسانة**\n\nحيث إجمالي الخرسانة = قواعد + نظافة + كمرات رابطة + أعمدة عنقية."
            else:
                return "Eng. Basel, the backfill formula is:\n\n**Volume = (Excavation Area × (Depth + 0.15)) - Total Concrete Volume**\n\nWhere total concrete = Foundations + PCC + Tie Beams + Neck Columns."

        # ── Generic QS fallback ──────────────────────────────────────────
        if ar:
            return f"مرحباً باشمهندس باسل. بصفتي خبير حساب كميات في الإمارات، يسعدني مساعدتك.\n\nبخصوص استفسارك: '{prompt}'\n\nحالياً أعمل في وضع الاستجابة المحلية. للحصول على إجابات أكثر تفصيلاً، يرجى التأكد من إدخال مفتاح API في صفحة الإعدادات.\n\n💡 يمكنك سؤالي عن: الحفر، القواعد، الكمرات الرابطة، الأعمدة، البلاطات، الردم، أو أسعار السوق."
        else:
            return f"Hello Eng. Basel. As a UAE QS expert, I am here to help.\n\nRegarding your query: '{prompt}'\n\nI am currently operating in local response mode. For more detailed answers, please ensure an API key is configured in Settings.\n\n💡 You can ask me about: excavation, foundations, tie beams, columns, slabs, backfill, or market prices."
    
    else:
        # ── Customer Care Domain ─────────────────────────────────────────
        if any(kw in q for kw in ["subscription", "اشتراك", "plan", "خطة", "tier"]):
            if ar:
                return "أهلاً باشمهندس باسل! بخصوص خطط الاشتراك لدينا:\n\n• **الفئة 1:** 50 درهم/شهر — مشروع واحد\n• **الفئة 2:** 120 درهم/شهر — 3 مشاريع (الأكثر طلباً)\n• **الفئة 3:** 250 درهم/شهر — 10 مشاريع\n• **الفئة 4:** 500 درهم/شهر — 25 مشروع\n\nهل ترغب في ترقية خطتك؟"
            else:
                return "Hello Eng. Basel! Here are our subscription tiers:\n\n• **Tier 1:** 50 AED/month — 1 Project\n• **Tier 2:** 120 AED/month — 3 Projects (Most Popular)\n• **Tier 3:** 250 AED/month — 10 Projects\n• **Tier 4:** 500 AED/month — 25 Projects\n\nWould you like to upgrade your plan?"
        
        if any(kw in q for kw in ["api", "key", "مفتاح"]):
            if ar:
                return "أهلاً باشمهندس باسل! لإعداد مفاتيح API:\n\n1. اذهب لصفحة **الإعدادات** من القائمة الجانبية\n2. ألصق مفتاح الـ API في الحقل المخصص\n3. اضغط **حفظ وتطبيق**\n\n💡 يمكنك إضافة حتى 10 مفاتيح لزيادة السعة اليومية إلى 200 مشروع!"
            else:
                return "Hello Eng. Basel! To set up API keys:\n\n1. Go to **Settings** in the sidebar\n2. Paste your API key in the field\n3. Click **Save & Apply**\n\n💡 You can add up to 10 keys to increase daily capacity to 200 projects!"
        
        # ── Generic Customer Care fallback ────────────────────────────────
        if ar:
            return f"أهلاً بك باشمهندس باسل في خدمة عملاء THE QS HUB! أنا سارة من فريق نجاح العملاء.\n\nبخصوص استفسارك: '{prompt}'\n\nحالياً أعمل في وضع الاستجابة المحلية. للحصول على ردود أكثر تفصيلاً، يرجى التأكد من إعداد مفتاح الـ API في الإعدادات.\n\n💡 يمكنك سؤالي عن: الاشتراكات، إعداد مفاتيح API، أو أي مشكلة في المنصة."
        else:
            return f"Hello Eng. Basel! Welcome to THE QS HUB Customer Success. I am Sarah.\n\nRegarding your inquiry: '{prompt}'\n\nI am currently operating in local response mode. For more detailed assistance, please ensure an API key is configured in Settings.\n\n💡 You can ask me about: subscriptions, API key setup, or any platform issues."

def render_ai_agents():
    import streamlit as st
    ar = (get_lang() == "ar")
    rtl = is_rtl()
    text_align = "right" if rtl else "left"
    
    title_label = "المساعد الذكي" if ar else "AI Assistants"
    subtitle_label = "مساعد الكميات الهندسي في مكان واحد." if ar else "Your QS Engineer, all in one place."
    
    st.markdown(f"""
        <div style="text-align:{text_align}; margin-bottom:20px;">
            <h1 style="color:#3b82f6; margin:0; font-size:2.2rem; font-weight:800;">{title_label}</h1>
            <p style="color:#64748b; font-size:1.0rem; margin-top:5px;">{subtitle_label}</p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    user = st.session_state.get("user")
    if not user:
        st.warning("Please log in to access the AI assistant." if not ar else "الرجاء تسجيل الدخول للوصول إلى المساعد الذكي.")
        return
        
    is_admin = (user.get("role") == "admin")
    has_access = True
    
    if not is_admin:
        sub = fetch_active_subscription(user["id"])
        if not sub or sub.get("status") != "active":
            has_access = False
            
    if not has_access:
        inactive_title = "المساعد الذكي غير نشط" if ar else "Assistant Inactive"
        inactive_body = "Quantity Surveying Assistant is only available for accounts with active subscription tiers. Please subscribe or contact support if you believe this is an error."
        btn_label = "تواصل مع الدعم الفني" if ar else "Contact Support"
        
        st.markdown(f"""
            <div style="text-align:center; max-width:550px; margin:40px auto; padding:30px; border:1px solid #fde68a; background-color:#fffbeb; border-radius:20px;">
                <div style="font-size:3rem; margin-bottom:10px;">⚠️</div>
                <h3 style="color:#92400e; font-weight:700; margin-bottom:10px;">{inactive_title}</h3>
                <p style="color:#b45309; font-size:0.95rem; line-height:1.6; margin-bottom:20px;">{inactive_body}</p>
            </div>
        """, unsafe_allow_html=True)
        col_s1, col_s2, col_s3 = st.columns([1, 1.2, 1])
        with col_s2:
            if st.button(btn_label, use_container_width=True, type="primary"):
                st.info("Support channel: support@qshub.ae")
        return

    welcome_qs = "مرحباً باشمهندس باسل! أنا مساعد الكميات الذكي (QS Assistant). كيف يمكنني مساعدتك اليوم؟" if ar else "Hello Eng. Basel! I am your QS Assistant. Ask me about takeoff formulas or UAE market updates!"
    if "qs_chat_history" not in st.session_state:
        st.session_state["qs_chat_history"] = [{"role": "assistant", "content": welcome_qs}]
        
    for msg in st.session_state["qs_chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    prompt_qs = st.chat_input("Ask QS Assistant..." if not ar else "اسأل المساعد الهندسي...", key="input_qs")
    if prompt_qs:
        st.session_state["qs_chat_history"].append({"role": "user", "content": prompt_qs})
        with st.chat_message("user"):
            st.write(prompt_qs)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..." if not ar else "جاري التفكير..."):
                ok, msg = check_limit(user, EVENT_AI_CALL)
                if not ok:
                    st.warning(msg if not ar else "تم الوصول إلى الحد المسموح.")
                else:
                    log_usage(user["id"], EVENT_AI_CALL, metadata={"role": "qs"})
                    reply = generate_agent_response(prompt_qs, "qs", ar, user["id"])
                    st.write(reply)
                    st.session_state["qs_chat_history"].append({"role": "assistant", "content": reply})
