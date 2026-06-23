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
            from utils.market_prices_logic import update_db_prices
            success, msg = update_db_prices()
            return "حدّثتُ قائمة الأسعار الاسترشادية بنجاح." if success else "Failed to update prices."
            
    elif role == "cc":
        if any(kw in q for kw in ["complain", "شكوى", "issue", "problem", "مشكلة"]):
            log_customer_complaint(user_id, prompt)
            # We don't return here so the LLM can generate a natural, empathetic response!
            
    elif role == "mgr":
        import re
        emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", q)
        target_email = emails[0] if emails else None
        
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
            
        # Dangerous commands (refund, cleanup, email all) have been disabled for security reasons.

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
        system_prompt = f"""You are "Sarah", the professional, highly empathetic Customer Support Agent for "THE QS HUB".
THE QS HUB is an advanced AI-powered SaaS platform for civil engineers and Quantity Surveyors (QS) in the UAE. It automates Quantity Takeoff (QTO) from architectural and structural blueprints (PDFs) and generates comprehensive Bill of Quantities (BOQ) schedules using indicative UAE market rates.
Your job is to answer questions about what the website does, explain our subscription plans, and handle general support.
If a user asks what the website does, explain that it's an AI-powered Quantity Takeoff platform that automatically calculates quantities from blueprints and creates priced BOQs using indicative UAE market data.
If a user complains or has an issue, BE EMPATHETIC and act like a real human agent. Apologize sincerely for the inconvenience, ask for more details to understand the issue, and reassure them that their issue has been officially logged in our system and forwarded to the Admin/AI Manager for review. Do not just output a generic robotic response.
You MUST NOT mention, refer to, or help with API keys under any circumstances.
"""
    else:
        system_prompt = f"""You are "The AI Manager" for "THE QS HUB".
You know everything about the site (automated Quantity Takeoff, BOQ generation, UAE market rates). You supervise the workflow and the other 2 agents.
You send a daily report to the admin, and you always warn if there's any failure.
You act as the CEO/Admin. Execute refunds via Dodo Payments if asked.
"""

    system_prompt += "\nCRITICAL: You must speak and understand both Arabic and English. You MUST reply in the exact same language the user writes in (Arabic for Arabic, English for English)."


    # Try AI API with retries for rate limits
    manager = get_key_manager()
    reply = ""
    success = False
    
    for _ in range(4):
        api_key, model_name = manager.get_key_and_model()
        if not api_key:
            break
            
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
            success = True
            break
        except Exception as e:
            print(f"AI AGENT ERROR (Retrying): {str(e)}")
            import time
            time.sleep(0.5)
            
    if not success:
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
                return "مهندسنا العزيز، معادلة حساب الحفر هي:\n\n**الحجم = (أطول بُعد + 2) × (أعرض بُعد + 2) × عمق الحفر**\n\nعمق الحفر الافتراضي = 1.25 م (حسب تقرير التربة).\nالإضافة (+2 م) تمثل مسافة العمل حول القاعدة من كل جانب."
            else:
                return "Dear Engineer, the excavation formula is:\n\n**Volume = (Longest Length + 2) × (Longest Width + 2) × Excavation Depth**\n\nDefault depth = 1.25 m (per geotechnical report).\nThe +2 m addition represents working space around the foundation on each side."
        
        if any(kw in q for kw in ["footing", "foundation", "قاعد", "أساس", "اساس"]):
            if ar:
                return "مهندسنا العزيز، لحساب خرسانة القواعد:\n\n**الحجم = الطول × العرض × العمق × العدد** (لكل نوع قاعدة)\n\nوخرسانة النظافة (PCC): **(الطول + 0.20) × (العرض + 0.20) × 0.10 × العدد**\n\nوالبيتومين: **(المساحة + المحيط × العمق) × العدد**"
            else:
                return "Dear Engineer, for foundation concrete:\n\n**Volume = Length × Width × Depth × Count** (per footing type)\n\nPCC (Blinding): **(Length + 0.20) × (Width + 0.20) × 0.10 × Count**\n\nBitumen: **(Area + Perimeter × Depth) × Count**"
        
        if any(kw in q for kw in ["tie beam", "كمرة رابطة", "كمرات رابطة", "tb"]):
            if ar:
                return "مهندسنا العزيز، لحساب الكمرات الرابطة:\n\n**خرسانة = العرض × العمق × الطول الإجمالي**\n**خرسانة النظافة = (العرض + 0.20) × 0.10 × الطول الإجمالي**\n**البيتومين = الطول الإجمالي × العمق × 2** (الوجهين)"
            else:
                return "Dear Engineer, for tie beams:\n\n**Concrete = Width × Depth × Total Length**\n**PCC = (Width + 0.20) × 0.10 × Total Length**\n**Bitumen = Total Length × Depth × 2** (both faces)"
        
        if any(kw in q for kw in ["column", "عمود", "أعمدة", "اعمدة"]):
            if ar:
                return "مهندسنا العزيز، لحساب خرسانة الأعمدة:\n\n**الحجم = الطول × العرض × الارتفاع × العدد**\n\nالارتفاعات الافتراضية: أرضي-أول = 4.0 م، أول-ثاني = 4.0 م، سطح = 3.5 م."
            else:
                return "Dear Engineer, for column concrete:\n\n**Volume = Length × Width × Height × Count**\n\nDefault heights: GF→1F = 4.0 m, 1F→2F = 4.0 m, Roof = 3.5 m."

        if any(kw in q for kw in ["slab", "بلاطة", "بلاطات", "سقف"]):
            if ar:
                return "مهندسنا العزيز، لحساب خرسانة البلاطات:\n\n**الحجم = مساحة البلاطة × السماكة**\n\nالسماكة الافتراضية = 0.20 م (200 مم). يُحسب لكل دور على حدة."
            else:
                return "Dear Engineer, for slab concrete:\n\n**Volume = Slab Area × Thickness**\n\nDefault thickness = 0.20 m (200 mm). Calculated per floor separately."
        
        if any(kw in q for kw in ["price", "سعر", "أسعار", "اسعار", "market"]):
            if ar:
                return "مهندسنا العزيز، أنا المسؤول عن تحديث أسعار السوق أسبوعياً. الأسعار الحالية تشمل 24 مادة بناء عبر 4 إمارات (دبي، أبوظبي، الشارقة، عجمان).\n\nأرسل لي **'تحديث الأسعار'** وسأقوم بتحديث قاعدة البيانات فوراً.\n\nيمكنك أيضاً مراجعة الأسعار في صفحة **أسعار السوق** من القائمة الجانبية."
            else:
                return "Dear Engineer, I manage weekly market price updates. Current database covers 24 construction materials across 4 emirates (Dubai, Abu Dhabi, Sharjah, Ajman).\n\nSend me **'update prices'** and I'll sync the database immediately.\n\nYou can also view prices under the **Market Prices** tab in the sidebar."

        if any(kw in q for kw in ["backfill", "ردم"]):
            if ar:
                return "مهندسنا العزيز، معادلة الردم:\n\n**الحجم = (مساحة الحفر × (عمق الحفر + 0.15)) - إجمالي حجم الخرسانة**\n\nحيث إجمالي الخرسانة = قواعد + نظافة + كمرات رابطة + أعمدة عنقية."
            else:
                return "Dear Engineer, the backfill formula is:\n\n**Volume = (Excavation Area × (Depth + 0.15)) - Total Concrete Volume**\n\nWhere total concrete = Foundations + PCC + Tie Beams + Neck Columns."

        # ── Generic QS fallback ──────────────────────────────────────────
        if ar:
            return f"مرحباً بك. بصفتي خبير حساب كميات في الإمارات، يسعدني مساعدتك.\n\nبخصوص استفسارك: '{prompt}'\n\nحالياً أعمل في وضع الاستجابة المحلية. للحصول على إجابات أكثر تفصيلاً، يرجى التأكد من إدخال مفتاح API في صفحة الإعدادات.\n\n💡 يمكنك سؤالي عن: الحفر، القواعد، الكمرات الرابطة، الأعمدة، البلاطات، الردم، أو أسعار السوق."
        else:
            return f"Hello. As a UAE QS expert, I am here to help.\n\nRegarding your query: '{prompt}'\n\nI am currently operating in local response mode. For more detailed answers, please ensure an API key is configured in Settings.\n\n💡 You can ask me about: excavation, foundations, tie beams, columns, slabs, backfill, or market prices."
    
    else:
        # ── Customer Care Domain ─────────────────────────────────────────
        if any(kw in q for kw in ["subscription", "اشتراك", "plan", "خطة", "tier"]):
            if ar:
                return "أهلاً بك! بخصوص خطط الاشتراك لدينا:\n\n• **الفئة 1:** 50 درهم/شهر — مشروع واحد\n• **الفئة 2:** 120 درهم/شهر — 3 مشاريع (الأكثر طلباً)\n• **الفئة 3:** 250 درهم/شهر — 10 مشاريع\n• **الفئة 4:** 500 درهم/شهر — 25 مشروع\n\nهل ترغب في ترقية خطتك؟"
            else:
                return "Hello! Here are our subscription tiers:\n\n• **Tier 1:** 50 AED/month — 1 Project\n• **Tier 2:** 120 AED/month — 3 Projects (Most Popular)\n• **Tier 3:** 250 AED/month — 10 Projects\n• **Tier 4:** 500 AED/month — 25 Projects\n\nWould you like to upgrade your plan?"
        
        if any(kw in q for kw in ["api", "key", "مفتاح"]):
            if ar:
                return "أهلاً بك! لإعداد مفاتيح API:\n\n1. اذهب لصفحة **الإعدادات** من القائمة الجانبية\n2. ألصق مفتاح الـ API في الحقل المخصص\n3. اضغط **حفظ وتطبيق**\n\n💡 يمكنك إضافة حتى 10 مفاتيح لزيادة السعة اليومية إلى 200 مشروع!"
            else:
                return "Hello! To set up API keys:\n\n1. Go to **Settings** in the sidebar\n2. Paste your API key in the field\n3. Click **Save & Apply**\n\n💡 You can add up to 10 keys to increase daily capacity to 200 projects!"
        
        # ── Generic Customer Care fallback ────────────────────────────────
        if ar:
            return f"أهلاً بك في خدمة عملاء THE QS HUB! أنا سارة من فريق نجاح العملاء.\n\nبخصوص استفسارك: '{prompt}'\n\nحالياً أعمل في وضع الاستجابة المحلية. للحصول على ردود أكثر تفصيلاً، يرجى التأكد من إعداد مفتاح الـ API في الإعدادات.\n\n💡 يمكنك سؤالي عن: الاشتراكات، إعداد مفاتيح API، أو أي مشكلة في المنصة."
        else:
            return f"Welcome to THE QS HUB Customer Success. I am Sarah.\n\nRegarding your inquiry: '{prompt}'\n\nI am currently operating in local response mode. For more detailed assistance, please ensure an API key is configured in Settings.\n\n💡 You can ask me about: subscriptions, API key setup, or any platform issues."

