"""
نظام الترجمة الثنائي — عربي / إنجليزي
=======================================
الاستخدام في أي ملف:
    from utils.i18n import t, get_lang, set_lang

    st.markdown(t("upload_title"))
    lang = get_lang()   # "en" أو "ar"
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  قاموس الترجمات الكامل
# ═══════════════════════════════════════════════════════════════════════════════
_TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── App / Navigation ──────────────────────────────────────────────────────
    "app_title":          {"en": "THE QS HUB",   "ar": "THE QS HUB"},
    "nav_home":           {"en": "Home",               "ar": "الرئيسية"},
    "nav_analysis":       {"en": "Analysis",           "ar": "التحليل"},
    "nav_projects":       {"en": "Projects",           "ar": "المشاريع"},
    "nav_profile":        {"en": "Profile",            "ar": "الملف الشخصي"},
    "nav_label":          {"en": "Navigate",              "ar": "تنقّل"},
    "theme_label":        {"en": "Theme",              "ar": "الثيم"},
    "theme_dark":         {"en": "Dark",               "ar": "غامق"},
    "theme_light":        {"en": "Light",              "ar": "فاتح"},
    "lang_toggle":        {"en": "العربية",            "ar": "English"},
    "caption_powered":    {"en": "THE QS HUB · AI-powered",
                           "ar": "حساب كميات فلل الإمارات · مدعوم بالذكاء الاصطناعي"},

    # ── Analysis page ─────────────────────────────────────────────────────────
    "analysis_title":     {"en": "Project Analysis",  "ar": "تحليل المشروع"},
    "project_name":       {"en": "Project Name",         "ar": "اسم المشروع"},
    "step_nav_go":        {"en": "Go",                   "ar": "انتقل"},

    # ── Steps ─────────────────────────────────────────────────────────────────
    "step1_label":        {"en": "Upload Drawings",       "ar": "رفع المخططات"},
    "step2_label":        {"en": "Classify Pages",        "ar": "تصنيف الصفحات"},
    "step3_label":        {"en": "Extract Data",          "ar": "استخراج البيانات"},
    "step4_label":        {"en": "Confirm Missing",       "ar": "تأكيد الناقص"},
    "step5_label":        {"en": "Apply Formulas",        "ar": "تطبيق المعادلات"},
    "step6_label":        {"en": "Review Results",        "ar": "مراجعة النتائج"},
    "step7_label":        {"en": "Arrange BOQ",           "ar": "ترتيب الكميات"},
    "step8_label":        {"en": "Download Excel",        "ar": "تحميل Excel"},

    # ── Step 1: Upload ────────────────────────────────────────────────────────
    "upload_title":       {"en": "## Step 1: Upload Your Drawings",
                           "ar": "## الخطوة 1: رفع المخططات"},
    "upload_caption":     {"en": "Upload Structural PDF and/or Architectural PDF",
                           "ar": "ارفع ملف PDF الإنشائي و/أو المعماري"},
    "upload_str_title":   {"en": "### Structural",    "ar": "### إنشائي"},
    "upload_arch_title":  {"en": "### Architectural", "ar": "### معماري"},
    "upload_str_hint":    {"en": "Foundations, Columns, Slabs, Beams",
                           "ar": "أساسات، أعمدة، بلاطات، جسور"},
    "upload_arch_hint":   {"en": "Floor Plans, Elevations, Schedules",
                           "ar": "مساقط، واجهات، جداول"},
    "upload_processing_str":  {"en": "Processing structural PDF...",
                               "ar": "جارٍ معالجة الملف الإنشائي..."},
    "upload_processing_arch": {"en": "Processing architectural PDF...",
                               "ar": "جارٍ معالجة الملف المعماري..."},
    "upload_success_str": {"en": "Structural",        "ar": "إنشائي"},
    "upload_success_arch":{"en": "Architectural",     "ar": "معماري"},
    "upload_pages":       {"en": "pages",                "ar": "صفحة"},
    "upload_total":       {"en": "Total pages loaded:", "ar": "إجمالي الصفحات المحمّلة:"},
    "upload_next_btn":    {"en": "Next → Classify Pages","ar": "التالي ← تصنيف الصفحات"},

    # ── Step 2: Classify ──────────────────────────────────────────────────────
    "classify_title":     {"en": "## Step 2: Classify Pages",
                           "ar": "## الخطوة 2: تصنيف الصفحات"},
    "classify_caption":   {"en": "AI identifies each page type automatically",
                           "ar": "الذكاء الاصطناعي يصنّف كل صفحة تلقائياً"},
    "classify_run_btn":   {"en": "Run AI Classification",
                           "ar": "تشغيل التصنيف بالذكاء الاصطناعي"},
    "classify_running":   {"en": "Classifying pages with AI...",
                           "ar": "جارٍ التصنيف بالذكاء الاصطناعي..."},
    "classify_done":      {"en": "Classification complete",
                           "ar": "اكتمل التصنيف"},
    "classify_next_btn":  {"en": "Next → Extract Data",
                           "ar": "التالي ← استخراج البيانات"},

    # ── Step 3: Extract ───────────────────────────────────────────────────────
    "extract_title":      {"en": "## Step 3: Extract Data",
                           "ar": "## الخطوة 3: استخراج البيانات"},
    "extract_caption":    {"en": "AI engine reads dimensions from your drawings",
                           "ar": "الذكاء الاصطناعي يقرأ الأبعاد من مخططاتك"},
    "extract_run_btn":    {"en": "Extract All Data",  "ar": "استخراج جميع البيانات"},
    "extract_running":    {"en": "Extracting data...",   "ar": "جارٍ الاستخراج..."},
    "extract_done":       {"en": "Extraction complete","ar": "اكتمل الاستخراج"},
    "extract_next_btn":   {"en": "Next → Confirm Data",  "ar": "التالي ← تأكيد البيانات"},

    # ── Step 4: Confirm ───────────────────────────────────────────────────────
    "confirm_title":      {"en": "## Step 4: Confirm & Fill Missing Data",
                           "ar": "## الخطوة 4: تأكيد البيانات الناقصة"},
    "confirm_caption":    {"en": "Review extracted values and fill any gaps manually",
                           "ar": "راجع القيم المستخرجة وأكمل الناقص يدوياً"},
    "confirm_next_btn":   {"en": "Next → Calculate",    "ar": "التالي ← الحساب"},
    "confirm_save_btn":   {"en": "Save Changes",     "ar": "حفظ التعديلات"},
    "confirm_saved":      {"en": "Saved",             "ar": "تم الحفظ"},

    # ── Step 5: Calculate ─────────────────────────────────────────────────────
    "calc_title":         {"en": "## Step 5: Apply QTO Formulas",
                           "ar": "## الخطوة 5: تطبيق معادلات الكميات"},
    "calc_run_btn":       {"en": "Calculate All Quantities",
                           "ar": "احسب جميع الكميات"},
    "calc_running":       {"en": "Calculating...",       "ar": "جارٍ الحساب..."},
    "calc_done":          {"en": "Calculation complete","ar": "اكتمل الحساب"},
    "calc_next_btn":      {"en": "Next → Review",        "ar": "التالي ← المراجعة"},

    # ── Step 6: Review ────────────────────────────────────────────────────────
    "review_title":       {"en": "## Step 6: Review Results",
                           "ar": "## الخطوة 6: مراجعة النتائج"},
    "review_next_btn":    {"en": "Next → Arrange BOQ",  "ar": "التالي ← ترتيب الكميات"},

    # ── Step 7: Arrange ───────────────────────────────────────────────────────
    "arrange_title":      {"en": "## Step 7: Arrange BOQ",
                           "ar": "## الخطوة 7: ترتيب جدول الكميات"},
    "arrange_next_btn":   {"en": "Next → Download",     "ar": "التالي ← التحميل"},

    # ── Step 8: Download ──────────────────────────────────────────────────────
    "download_title":     {"en": "## Step 8: Download Excel Report",
                           "ar": "## الخطوة 8: تحميل تقرير Excel"},
    "download_btn":       {"en": "Download BOQ Excel","ar": "تحميل Excel للكميات"},
    "download_done":      {"en": "Report ready!",     "ar": "التقرير جاهز!"},

    # ── Sidebar ───────────────────────────────────────────────────────────────
    "sidebar_title":      {"en": "Project Settings", "ar": "إعدادات المشروع"},
    "sidebar_areas":      {"en": "### Areas",         "ar": "### المساحات"},
    "sidebar_dims":       {"en": "### Dimensions",    "ar": "### الأبعاد"},
    "sidebar_heights":    {"en": "### Heights",       "ar": "### الارتفاعات"},
    "num_floors":         {"en": "Number of Floors",     "ar": "عدد الطوابق"},
    "gf_area":            {"en": "GF Area (m²)",         "ar": "مساحة الأرضي (م²)"},
    "f1_area":            {"en": "1F Area (m²)",         "ar": "مساحة الأول (م²)"},
    "f2_area":            {"en": "2F Area (m²)",         "ar": "مساحة الثاني (م²)"},
    "roof_area":          {"en": "Roof Area (m²)",       "ar": "مساحة السطح (م²)"},
    "plot_area":          {"en": "Plot Area (m²)",       "ar": "مساحة القطعة (م²)"},
    "ext_perimeter":      {"en": "External Perimeter (m)","ar": "المحيط الخارجي (م)"},
    "longest_length":     {"en": "Longest Length (m)",   "ar": "أطول بُعد (م)"},
    "longest_width":      {"en": "Longest Width (m)",    "ar": "أعرض بُعد (م)"},
    "roof_perimeter":     {"en": "Roof Perimeter (m)",   "ar": "محيط السطح (م)"},
    "compound_len":       {"en": "Compound Wall (m)",    "ar": "طول السور (م)"},
    "gf_height":          {"en": "GF Height (m)",        "ar": "ارتفاع الأرضي (م)"},
    "f1_height":          {"en": "1F Height (m)",        "ar": "ارتفاع الأول (م)"},
    "f2_height":          {"en": "2F Height (m)",        "ar": "ارتفاع الثاني (م)"},

    # ── Common / Shared ───────────────────────────────────────────────────────
    "yes":                {"en": "Yes",                  "ar": "نعم"},
    "no":                 {"en": "No",                   "ar": "لا"},
    "save":               {"en": "Save",                 "ar": "حفظ"},
    "cancel":             {"en": "Cancel",               "ar": "إلغاء"},
    "loading":            {"en": "Loading...",           "ar": "جارٍ التحميل..."},
    "error":              {"en": "Error",                "ar": "خطأ"},
    "warning":            {"en": "Warning",              "ar": "تحذير"},
    "success":            {"en": "Success",              "ar": "نجاح"},
    "total":              {"en": "Total",                "ar": "الإجمالي"},
    "quantity":           {"en": "Quantity",             "ar": "الكمية"},
    "unit":               {"en": "Unit",                 "ar": "الوحدة"},
    "description":        {"en": "Description",         "ar": "الوصف"},
    "section":            {"en": "Section",              "ar": "القسم"},
    "floor":              {"en": "Floor",                "ar": "الطابق"},
    "ground_floor":       {"en": "Ground Floor",        "ar": "الدور الأرضي"},
    "first_floor":        {"en": "1st Floor",           "ar": "الدور الأول"},
    "second_floor":       {"en": "2nd Floor",           "ar": "الدور الثاني"},
    "roof":               {"en": "Roof",                "ar": "السطح"},
    "substructure":       {"en": "Sub-Structure",       "ar": "الأعمال تحت الأرض"},
    "superstructure":     {"en": "Super-Structure",     "ar": "الأعمال العلوية"},
    "finishes":           {"en": "Finishes",            "ar": "التشطيبات"},
    "openings":           {"en": "Openings",            "ar": "الفتحات"},

    # ── BOQ items ─────────────────────────────────────────────────────────────
    "boq_excavation":     {"en": "Excavation",          "ar": "أعمال الحفر"},
    "boq_backfill":       {"en": "Backfill",            "ar": "الردم"},
    "boq_blinding":       {"en": "Blinding Concrete",   "ar": "خرسانة النظافة"},
    "boq_footings":       {"en": "Footings",            "ar": "القواعد"},
    "boq_tie_beams":      {"en": "Tie Beams",           "ar": "الكمرات الرابطة"},
    "boq_columns":        {"en": "Columns",             "ar": "الأعمدة"},
    "boq_slabs":          {"en": "Slabs",               "ar": "البلاطات"},
    "boq_beams":          {"en": "Beams",               "ar": "الكمرات"},
    "boq_walls":          {"en": "Walls",               "ar": "الجدران"},
    "boq_plastering":     {"en": "Plastering",          "ar": "اللياسة"},
    "boq_tiling":         {"en": "Tiling",              "ar": "البلاط"},
    "boq_painting":       {"en": "Painting",            "ar": "الدهان"},
    "boq_doors":          {"en": "Doors",               "ar": "الأبواب"},
    "boq_windows":        {"en": "Windows",             "ar": "النوافذ"},

    # ── AI / Key status ───────────────────────────────────────────────────────
    "key_status":         {"en": "API Key Status",      "ar": "حالة مفاتيح API"},
    "key_remaining":      {"en": "Requests remaining today",
                           "ar": "الطلبات المتبقية اليوم"},
    "key_exhausted":      {"en": "All keys exhausted — resets at midnight UTC",
                           "ar": "جميع المفاتيح منتهية — تُجدَّد عند منتصف الليل"},

    # ── Site Pages (Home, Projects, Profile) ──────────────────────────────────
    "home_title":         {"en": "THE QS HUB", "ar": "THE QS HUB"},
    "home_subtitle":      {"en": "Quantity take off for villa projects in Uae",
                           "ar": "حصر الكميات لمشاريع الفلل في الإمارات"},
    "home_workflow":      {"en": "Workflow", "ar": "خطوات العمل"},
    "home_boq_items":     {"en": "BOQ items", "ar": "بنود الكميات"},
    "home_ref_data":      {"en": "Reference data", "ar": "بيانات مرجعية"},
    "home_engine":        {"en": "Engine", "ar": "المحرك"},
    "home_metric_steps":  {"en": "8 steps", "ar": "8 خطوات"},
    "home_metric_items":  {"en": "74 items", "ar": "74 بنداً"},
    "home_metric_pts":    {"en": "640 pts", "ar": "640 نقطة"},
    "home_metric_ai":     {"en": "Proprietary AI", "ar": "ذكاء اصطناعي"},

    "home_new_metric1_title": {"en": "items extracted", "ar": "عناصر مستخرجة"},
    "home_new_metric1_val":   {"en": "+50 item", "ar": "+50 عنصر"},
    "home_new_metric2_title": {"en": "accuracy and confidance rate", "ar": "معدل الدقة والثقة"},
    "home_new_metric2_val":   {"en": "+80%", "ar": "+80%"},
    "home_attention":         {"en": "**Attention:**\n\n1- The system is designed to save time and effort. To guarantee the results, engineer's review is a must.\n\n2- Results quality of the system depends on the quality of the drawings and drawings classification accuracy.", "ar": "**تنبيه:**\n\n1- النظام مصمم لتوفير الوقت والجهد، ومراجعة المهندس ضرورية لضمان النتائج.\n\n2- جودة نتائج النظام تعتمد على جودة الرسومات ودقة تصنيف الرسومات."},
    "unit_m2":            {"en": "m²", "ar": "م²"},
    "home_start_btn":     {"en": "Start New Analysis", "ar": "ابدأ مشروع جديد"},
    "home_how_title":     {"en": "#### How it works", "ar": "#### كيف يعمل"},
    "home_how_text":      {"en": "1. **Upload** STR + ARCH drawings\n2. **Classify** every page (AI vision)\n3. **Extract** quantities (tables + vector + AI)\n4. **Confirm** the few values not on the drawings\n5. **Apply** the exact QTO formulas\n6. **Review** results — Sub / Super / Arch\n7. **Arrange** the BOQ (+ optional pricing)\n8. **Download** the final Excel",
                           "ar": "1. **رفع** المخططات الإنشائية والمعمارية\n2. **تصنيف** كل صفحة (بالذكاء الاصطناعي)\n3. **استخراج** الكميات (جداول + ذكاء اصطناعي)\n4. **تأكيد** القيم غير الموجودة بالمخططات\n5. **تطبيق** معادلات الحصر بدقة\n6. **مراجعة** النتائج — تحت/فوق الأرض والتشطيبات\n7. **ترتيب** جدول الكميات (+ تسعير اختياري)\n8. **تحميل** ملف Excel النهائي"},
    "home_what_title":    {"en": "#### What you get", "ar": "#### ماذا ستحصل"},
    "home_what_text":     {"en": "- Sub-structure, super-structure & finishes\n- Per-floor columns, beams & slabs\n- Measured tie-beam / beam lengths (vector)\n- Validation against 640 real villas\n- Professional Excel BOQ (+ pricing)",
                           "ar": "- حصر الأعمال تحت وفوق الأرض والتشطيبات\n- حصر الأعمدة والجسور والبلاطات لكل طابق\n- أطوال الجسور الرابطة مقاسة بدقة\n- مطابقة مع 640 فيلا حقيقية\n- جدول كميات Excel احترافي (+ تسعير)"},
    "home_tip":           {"en": "Tip: open **⚙️ Settings** to configure your API key & defaults, and **Projects** to revisit past BOQs.",
                           "ar": "تلميح: افتح **⚙️ الإعدادات** لتهيئة مفتاح الـ API، و**المشاريع** لمراجعة الجداول السابقة."},

    "proj_title":         {"en": "Projects", "ar": "المشاريع"},
    "proj_current":       {"en": "Current project", "ar": "المشروع الحالي"},
    "proj_villa_type":    {"en": "Villa type", "ar": "نوع الفيلا"},
    "proj_gf_area":       {"en": "GF area", "ar": "مساحة الأرضي"},
    "proj_levels":        {"en": "Levels", "ar": "الطوابق"},
    "proj_updated":       {"en": "Updated", "ar": "آخر تحديث"},
    "proj_open_btn":      {"en": "Open in Analysis", "ar": "فتح في التحليل"},
    "proj_no_active":     {"en": "No active project yet. Start one in Analysis.", "ar": "لا يوجد مشروع حالي. ابدأ واحداً من التحليل."},
    "proj_saved":         {"en": "Saved BOQs", "ar": "جدول الكميات المحفوظة"},
    "proj_items":         {"en": "items", "ar": "بند"},
    "proj_no_saved":      {"en": "No saved BOQs yet — save one from the BOQ step.", "ar": "لا يوجد جداول محفوظة — احفظ واحداً من خطوة الترتيب."},

    "prof_title":         {"en": "Profile", "ar": "الملف الشخصي"},
    "prof_name":          {"en": "Full name", "ar": "الاسم الكامل"},
    "prof_company":       {"en": "Company", "ar": "الشركة"},
    "prof_email":         {"en": "Email", "ar": "البريد الإلكتروني"},
    "prof_role":          {"en": "Role", "ar": "الدور"},
    "prof_save_btn":      {"en": "Save profile", "ar": "حفظ الملف"},
    "prof_saved":         {"en": "Profile saved.", "ar": "تم حفظ الملف الشخصي."},
    "prof_signed_in":     {"en": "Signed in as", "ar": "مسجل الدخول باسم"},

    # ── Landing Page ──────────────────────────────────────────────────────────
    "landing_slogan":     {"en": "AI powered assistant for quantity taking-off for villas project in the UAE & more.",
                           "ar": "مساعد مدعوم بالذكاء الاصطناعي لحصر كميات مشاريع الفلل في الإمارات والمزيد."},
    "landing_cta":        {"en": "Access Platform",         "ar": "الدخول إلى المنصة"},
    "landing_why_title":  {"en": "Why Choose THE QS HUB?","ar": "لماذا تختار THE QS HUB؟"},
    "landing_f1_title":   {"en": "UR QS ASSISTANT", "ar": "مساعد QS الخاص بك"},
    "landing_f1_body":    {"en": "SAVE TIME AND EFFORTS TO COMPLETE +80% FROM YOUR VILLA PROJECT BOQ WITH 80% AVERAGE ACCURACY", "ar": "وفر الوقت والجهد لإنجاز أكثر من 80% من جدول كميات مشروع الفيلا الخاص بك بمتوسط دقة 80%"},
    "landing_f2_title":   {"en": "VECTOR PDF DRAWINGS", "ar": "مخططات Vector PDF"},
    "landing_f2_body":    {"en": "HELPS YOU IN EXTRACTING +50 ITEMS USING (VECTOR) PDF DRAWINGS", "ar": "يساعدك في استخراج أكثر من 50 عنصراً باستخدام مخططات Vector PDF"},
    "landing_f3_title":   {"en": "UNMATCHED SPEED & ACCURACY", "ar": "سرعة ودقة غير مسبوقة"},
    "landing_f3_body":    {"en": "Get your BOQ ready in minutes, not days.<br/><br/>Our intelligent system features a self-learning memory loop, guaranteeing continuous accuracy improvements from one project to the next.", "ar": "احصل على جدول الكميات في دقائق بدلاً من أيام.<br/><br/>بفضل تقنية التعلم الذاتي، نضمن لك تحسن دقة النظام باستمرار من مشروع لآخر."},
    "landing_pricing_title": {"en": "Simple, Transparent Pricing", "ar": "أسعار بسيطة وشفافة"},
    "landing_popular":    {"en": "MOST POPULAR",             "ar": "الأكثر طلباً"},
    "landing_per_month":  {"en": "per month",                "ar": "شهرياً"},
    "landing_tier1_feat1":{"en": "1 Project",                "ar": "مشروع واحد"},
    "landing_tier1_feat2":{"en": "Basic Support",            "ar": "دعم أساسي"},
    "landing_tier1_feat3":{"en": "Core AI Features",         "ar": "ميزات الذكاء الأساسية"},
    "landing_tier2_feat1":{"en": "3 Projects",               "ar": "3 مشاريع"},
    "landing_tier2_feat2":{"en": "Email Support",            "ar": "دعم بريد إلكتروني"},
    "landing_tier2_feat3":{"en": "Full AI Agents",           "ar": "وكلاء الذكاء الكاملون"},
    "landing_tier3_feat1":{"en": "10 Projects",              "ar": "10 مشاريع"},
    "landing_tier3_feat2":{"en": "Priority Support",         "ar": "دعم ذو أولوية"},
    "landing_tier3_feat3":{"en": "Market Intelligence",      "ar": "ذكاء السوق"},
    "landing_tier4_feat1":{"en": "25 Projects",              "ar": "25 مشروعاً"},
    "landing_tier4_feat2":{"en": "24/7 Dedicated Support",   "ar": "دعم مخصص 24/7"},
    "landing_tier4_feat3":{"en": "Unlimited AI Access",      "ar": "وصول ذكاء اصطناعي غير محدود"},

    # ── Auth Page ─────────────────────────────────────────────────────────────
    "auth_welcome":       {"en": "Welcome Back",             "ar": "مرحباً بعودتك"},
    "auth_subtitle":      {"en": "Sign in to access THE QS HUB","ar": "سجّل دخولك للوصول إلى THE QS HUB"},
    "auth_login_tab":     {"en": "🔒 Secure Login",          "ar": "🔒 تسجيل الدخول"},
    "auth_signup_tab":    {"en": "✨ Create Account",         "ar": "✨ إنشاء حساب"},
    "auth_email":         {"en": "Email Address",            "ar": "البريد الإلكتروني"},
    "auth_password":      {"en": "Password",                 "ar": "كلمة المرور"},
    "auth_signin_btn":    {"en": "Sign In",                  "ar": "تسجيل الدخول"},
    "auth_or_with":       {"en": "Or continue with",         "ar": "أو المتابعة بـ"},
    "auth_signup_info":   {"en": "Choose your subscription tier and create your account.",
                           "ar": "اختر خطة الاشتراك وأنشئ حسابك."},
    "auth_confirm_pw":    {"en": "Confirm Password",         "ar": "تأكيد كلمة المرور"},
    "auth_select_plan":   {"en": "Select Plan",              "ar": "اختر خطة الاشتراك"},
    "auth_plan1":         {"en": "Tier 1: 50 AED / month (1 Project)",           "ar": "الفئة 1: 50 درهم / شهر (مشروع واحد)"},
    "auth_plan2":         {"en": "Tier 2: 120 AED / month (3 Projects) - Popular","ar": "الفئة 2: 120 درهم / شهر (3 مشاريع) - الأكثر طلباً"},
    "auth_plan3":         {"en": "Tier 3: 250 AED / month (10 Projects)",        "ar": "الفئة 3: 250 درهم / شهر (10 مشاريع)"},
    "auth_plan4":         {"en": "Tier 4: 500 AED / month (25 Projects)",        "ar": "الفئة 4: 500 درهم / شهر (25 مشروعاً)"},
    "auth_create_btn":    {"en": "Create Account & Subscribe",   "ar": "إنشاء الحساب والاشتراك"},
    "auth_authenticating":{"en": "Authenticating...",        "ar": "جارٍ التحقق..."},
    "auth_welcome_back":  {"en": "Welcome back!",            "ar": "مرحباً بعودتك!"},
    "auth_invalid":       {"en": "Invalid email or password. Please try again.", "ar": "البريد الإلكتروني أو كلمة المرور غير صحيحة."},
    "auth_pw_mismatch":   {"en": "Passwords do not match.",  "ar": "كلمتا المرور غير متطابقتين."},
    "auth_pw_mismatch":   {"en": "Passwords do not match.",  "ar": "كلمة المرور غير متطابقة."},
    "auth_creating":      {"en": "Creating account...",      "ar": "جارٍ إنشاء الحساب..."},
    "auth_redirect_paddle":{"en": "Redirecting to secure Paddle checkout for", "ar": "جارٍ التحويل إلى بوابة الدفع Paddle لـ"},

    # ── Admin & Shared new pages ───────────────────────────────────────────────
    "nav_market":         {"en": "Market Prices",            "ar": "أسعار السوق"},
    "nav_agents":         {"en": "AI Assistant",             "ar": "المساعد الذكي"},
    "nav_billing":        {"en": "Billing",                  "ar": "الفواتير والاشتراك"},
    "nav_legal":          {"en": "Legal",                    "ar": "القانوني والامتثال"},
    "nav_comparison":     {"en": "Plan Comparison",          "ar": "مقارنة المخططات"},
    "nav_admin":          {"en": "Admin Dashboard",          "ar": "لوحة التحكم"},
    "logout_btn":         {"en": "Logout",                   "ar": "تسجيل الخروج"},
    "logged_in_as":       {"en": "Logged in as:",            "ar": "مسجل الدخول:"},
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════

def get_lang() -> str:
    """يرجع اللغة الحالية: 'en' أو 'ar'."""
    try:
        import streamlit as st
        return st.session_state.get("lang", "en")
    except Exception:
        return "en"


def set_lang(lang: str):
    """يضبط اللغة: 'en' أو 'ar'."""
    try:
        import streamlit as st
        st.session_state["lang"] = lang
    except Exception:
        pass


def is_rtl() -> bool:
    """هل الواجهة من اليمين لليسار؟"""
    return get_lang() == "ar"


def t(key: str, **kwargs) -> str:
    """
    يرجع النص المترجم للمفتاح المعطى.
    يدعم استبدال المتغيرات: t("upload_total", count=12)
    إذا لم يُوجد المفتاح يُرجع المفتاح نفسه.
    """
    lang = get_lang()
    entry = _TRANSLATIONS.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def apply_rtl_css():
    """
    يُطبّق CSS يجعل الواجهة من اليمين لليسار عند اختيار العربية.
    استدعِه مرة واحدة في app.py بعد تحديد اللغة.
    """
    import streamlit as st
    if is_rtl():
        st.markdown("""
        <style>
        /* RTL layout for Arabic */
        html, body, .stApp, [data-testid="stAppViewContainer"],
        .main, section, article { 
            direction: rtl !important; 
            font-family: 'Tajawal', 'Cairo', 'Arial', sans-serif;
        }

        /* === SIDEBAR ON RIGHT SIDE for RTL === */
        [data-testid="stSidebar"] {
            direction: rtl !important;
            left: unset !important;
            right: 0 !important;
            transition: right 0.3s ease, width 0.3s ease, transform 0.3s ease !important;
        }
        /* When collapsed, Streamlit uses negative margin-left or transform to hide it.
           Override so it slides off to the RIGHT instead of left */
        [data-testid="stSidebar"][aria-expanded="false"] {
            right: -245px !important;
            left: unset !important;
            transform: none !important;
            margin-left: unset !important;
        }
        [data-testid="stSidebar"] > div:first-child { direction: rtl !important; }

        /* Move the collapse button */
        [data-testid="stSidebar"] button[kind="header"] {
            right: unset !important;
            left: 0.5rem !important;
        }
        
        /* Collapsed sidebar toggle button - move to right side */
        [data-testid="collapsedControl"] {
            left: unset !important;
            right: 0.5rem !important;
        }

        /* Push main content to the left when sidebar is open */
        [data-testid="stAppViewContainer"] > .main {
            margin-right: 0 !important;
            margin-left: 0 !important;
        }

        /* === COMPACT SIDEBAR SPACING === */
        [data-testid="stSidebar"] .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        [data-testid="stSidebar"] hr {
            margin-top: 4px !important;
            margin-bottom: 4px !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        [data-testid="stSidebar"] .stRadio > div {
            gap: 2px !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            padding: 4px 8px !important;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            padding: 0 !important;
        }

        /* Text alignment */
        h1, h2, h3, h4, h5, h6, p, label, div.stMarkdown,
        .stTextInput label, .stSelectbox label,
        .stNumberInput label, .stFileUploader label {
            text-align: right !important;
        }
        
        /* Force font on common text elements EXCEPT material icons */
        h1, h2, h3, h4, h5, h6, p, label, div.stMarkdown {
            font-family: 'Tajawal', 'Cairo', 'Arial', sans-serif !important;
        }

        /* Buttons */
        .stButton > button { direction: rtl; font-family: 'Tajawal', 'Cairo', 'Arial', sans-serif !important; }

        /* Tables */
        table { direction: rtl; }
        th, td { text-align: right !important; font-family: 'Tajawal', 'Cairo', 'Arial', sans-serif !important; }

        /* Progress / steps */
        .step-box { direction: rtl; }

        /* Flip number inputs arrow direction */
        [data-testid="stNumberInput"] { direction: ltr; }
        [data-testid="stNumberInput"] label { direction: rtl; text-align: right; }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        html, body, [data-testid="stAppViewContainer"], .main { 
            direction: ltr !important; 
            font-family: 'Outfit', 'Segoe UI', sans-serif;
        }
        h1, h2, h3, h4, h5, h6, p, label, div.stMarkdown { 
            text-align: left !important;
        }
        h1, h2, h3, h4, h5, h6, p, label, div.stMarkdown {
            font-family: 'Outfit', 'Segoe UI', sans-serif !important; 
        }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        """, unsafe_allow_html=True)
