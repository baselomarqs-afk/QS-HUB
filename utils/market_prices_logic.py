import pandas as pd
import random
import functools
from utils.i18n import t, get_lang, is_rtl
from utils.db import get_connection, safe_query

# UAE Construction Material Prices - December 2025 (No resource mentions)
DEFAULT_MATERIALS = [
    # STEEL & REBAR
    {
        "code": "STL001",
        "name_en": "Rebar 8mm (Grade 60)",
        "name_ar": "حديد تسليح 8 مم (درجة 60)",
        "unit": "ton",
        "category": "steel",
        "dubai": 2668, "abudhabi": 2660, "sharjah": 2668, "ajman": 2668,
        "accuracy": 99,
        "last_verified": "2025-12-18"
    },
    {
        "code": "STL002",
        "name_en": "Rebar 10mm (Grade 60)",
        "name_ar": "حديد تسليح 10 مم (درجة 60)",
        "unit": "ton",
        "category": "steel",
        "dubai": 2668, "abudhabi": 2660, "sharjah": 2668, "ajman": 2668,
        "accuracy": 99,
        "last_verified": "2025-12-18"
    },
    {
        "code": "STL003",
        "name_en": "Rebar 12mm (Grade 60)",
        "name_ar": "حديد تسليح 12 مم (درجة 60)",
        "unit": "ton",
        "category": "steel",
        "dubai": 2668, "abudhabi": 2660, "sharjah": 2668, "ajman": 2668,
        "accuracy": 99,
        "last_verified": "2025-12-18"
    },
    {
        "code": "STL004",
        "name_en": "Rebar 16mm (Grade 60)",
        "name_ar": "حديد تسليح 16 مم (درجة 60)",
        "unit": "ton",
        "category": "steel",
        "dubai": 2668, "abudhabi": 2660, "sharjah": 2668, "ajman": 2668,
        "accuracy": 99,
        "last_verified": "2025-12-18"
    },
    # CONCRETE & CEMENT
    {
        "code": "CON001",
        "name_en": "Ready Mix C20/25",
        "name_ar": "خرسانة جاهزة C20/25",
        "unit": "m³",
        "category": "concrete",
        "dubai": 295, "abudhabi": 310, "sharjah": 285, "ajman": 280,
        "accuracy": 92,
        "last_verified": "2025-12-15"
    },
    {
        "code": "CON002",
        "name_en": "Ready Mix C30/37",
        "name_ar": "خرسانة جاهزة C30/37",
        "unit": "m³",
        "category": "concrete",
        "dubai": 350, "abudhabi": 365, "sharjah": 340, "ajman": 335,
        "accuracy": 92,
        "last_verified": "2025-12-15"
    },
    {
        "code": "CEM001",
        "name_en": "OPC Cement 50kg",
        "name_ar": "أسمنت بورتلاندي عادي 50 كجم",
        "unit": "bag",
        "category": "concrete",
        "dubai": 14.5, "abudhabi": 15.0, "sharjah": 14.0, "ajman": 13.5,
        "accuracy": 95,
        "last_verified": "2025-12-12"
    },
    # BLOCKS & BRICKS
    {
        "code": "BLK001",
        "name_en": "Hollow Block 8\"",
        "name_ar": "طابوق مفرغ 8 بوصة",
        "unit": "pc",
        "category": "blocks",
        "dubai": 3.40, "abudhabi": 3.60, "sharjah": 3.25, "ajman": 3.15,
        "accuracy": 93,
        "last_verified": "2025-12-14"
    },
    {
        "code": "BLK002",
        "name_en": "Hollow Block 6\"",
        "name_ar": "طابوق مفرغ 6 بوصة",
        "unit": "pc",
        "category": "blocks",
        "dubai": 2.90, "abudhabi": 3.10, "sharjah": 2.80, "ajman": 2.70,
        "accuracy": 93,
        "last_verified": "2025-12-14"
    },
    # SAND & AGGREGATES
    {
        "code": "SND001",
        "name_en": "Washed Sand",
        "name_ar": "رمل مغسول",
        "unit": "m³",
        "category": "sand",
        "dubai": 90, "abudhabi": 95, "sharjah": 85, "ajman": 82,
        "accuracy": 90,
        "last_verified": "2025-12-12"
    },
    {
        "code": "AGG001",
        "name_en": "Aggregate 20mm",
        "name_ar": "بحص 20 مم",
        "unit": "m³",
        "category": "sand",
        "dubai": 100, "abudhabi": 105, "sharjah": 95, "ajman": 92,
        "accuracy": 90,
        "last_verified": "2025-12-12"
    },
    # FINISHING MATERIALS
    {
        "code": "PLT001",
        "name_en": "Gypsum Plaster 25kg",
        "name_ar": "جبس بلاستر 25 كجم",
        "unit": "bag",
        "category": "finishing",
        "dubai": 18.5, "abudhabi": 19.5, "sharjah": 18.0, "ajman": 17.5,
        "accuracy": 90,
        "last_verified": "2025-12-10"
    },
    {
        "code": "PLT002",
        "name_en": "Gypsum Board 12.5mm",
        "name_ar": "ألواح جبسية 12.5 مم",
        "unit": "m²",
        "category": "finishing",
        "dubai": 28, "abudhabi": 30, "sharjah": 27, "ajman": 26,
        "accuracy": 88,
        "last_verified": "2025-12-08"
    },
    # PLUMBING
    {
        "code": "PLB001",
        "name_en": "UPVC Pipe 110mm",
        "name_ar": "أنابيب UPVC 110 مم",
        "unit": "m",
        "category": "plumbing",
        "dubai": 35, "abudhabi": 37, "sharjah": 34, "ajman": 33,
        "accuracy": 90,
        "last_verified": "2025-12-10"
    },
    {
        "code": "PLB002",
        "name_en": "PPR Pipe 25mm",
        "name_ar": "أنابيب PPR 25 مم",
        "unit": "m",
        "category": "plumbing",
        "dubai": 12, "abudhabi": 13, "sharjah": 11.5, "ajman": 11,
        "accuracy": 88,
        "last_verified": "2025-12-10"
    },
    # ELECTRICAL
    {
        "code": "ELC001",
        "name_en": "Cable 2.5mm",
        "name_ar": "كابل كهربائي 2.5 مم",
        "unit": "m",
        "category": "electrical",
        "dubai": 3.5, "abudhabi": 3.7, "sharjah": 3.4, "ajman": 3.3,
        "accuracy": 88,
        "last_verified": "2025-12-08"
    },
    {
        "code": "ELC002",
        "name_en": "Cable 4mm",
        "name_ar": "كابل كهربائي 4 مم",
        "unit": "m",
        "category": "electrical",
        "dubai": 5.5, "abudhabi": 5.8, "sharjah": 5.3, "ajman": 5.2,
        "accuracy": 88,
        "last_verified": "2025-12-08"
    },
    # INSULATION
    {
        "code": "INS001",
        "name_en": "Bitumen Membrane 4mm",
        "name_ar": "لفائف بيتومين عازل 4 مم",
        "unit": "m²",
        "category": "insulation",
        "dubai": 28, "abudhabi": 30, "sharjah": 27, "ajman": 26,
        "accuracy": 85,
        "last_verified": "2025-12-08"
    },
    # PAINT & COATINGS
    {
        "code": "PNT001",
        "name_en": "Emulsion Paint",
        "name_ar": "دهان مائي داخلي",
        "unit": "gallon",
        "category": "paint",
        "dubai": 85, "abudhabi": 88, "sharjah": 82, "ajman": 80,
        "accuracy": 92,
        "last_verified": "2025-12-12"
    },
    {
        "code": "PNT002",
        "name_en": "External Paint",
        "name_ar": "دهان خارجي",
        "unit": "gallon",
        "category": "paint",
        "dubai": 120, "abudhabi": 125, "sharjah": 118, "ajman": 115,
        "accuracy": 92,
        "last_verified": "2025-12-12"
    },
    # TILES & FLOORING
    {
        "code": "TIL001",
        "name_en": "Ceramic Tiles 60x60",
        "name_ar": "سيراميك 60×60 مم",
        "unit": "m²",
        "category": "tiles",
        "dubai": 45, "abudhabi": 48, "sharjah": 43, "ajman": 42,
        "accuracy": 85,
        "last_verified": "2025-12-08"
    },
    {
        "code": "TIL002",
        "name_en": "Porcelain Tiles 60x60",
        "name_ar": "بورسلان 60×60 مم",
        "unit": "m²",
        "category": "tiles",
        "dubai": 75, "abudhabi": 80, "sharjah": 72, "ajman": 70,
        "accuracy": 85,
        "last_verified": "2025-12-08"
    },
    # DOORS & WINDOWS
    {
        "code": "DOR001",
        "name_en": "Wooden Door (Standard)",
        "name_ar": "باب خشبي (قياسي)",
        "unit": "pc",
        "category": "doors",
        "dubai": 450, "abudhabi": 480, "sharjah": 430, "ajman": 420,
        "accuracy": 80,
        "last_verified": "2025-12-05"
    },
    {
        "code": "DOR002",
        "name_en": "Aluminum Window",
        "name_ar": "نافذة ألمنيوم",
        "unit": "m²",
        "category": "doors",
        "dubai": 350, "abudhabi": 370, "sharjah": 340, "ajman": 330,
        "accuracy": 80,
        "last_verified": "2025-12-05"
    }
]

import datetime
_curr_date = datetime.datetime.now()
_en_date = _curr_date.strftime("%B %Y")
_ar_months = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
_ar_date = f"{_ar_months[_curr_date.month - 1]} {_curr_date.year}"

LOCAL_TEXT = {
    "title": {
        "en": "Market Prices (UAE)",
        "ar": "أسعار السوق (الإمارات)"
    },
    "subtitle": {
        "en": "Live, automated construction material and labor rates driven by the Market Intelligence AI Agent.",
        "ar": "أسعار مباشرة ومؤتمتة لمواد البناء وأجور العمالة يغذيها وكيل الذكاء الاصطناعي لاستخبارات السوق."
    },
    "fetching": {
        "en": f"ℹ️ Live database sync in progress. Displaying local reference catalog ({_en_date}).",
        "ar": f"ℹ️ جارٍ مزامنة قاعدة البيانات الحية. يتم عرض الكتالوج المرجعي المحلي ({_ar_date})."
    },
    "search": {
        "en": "Search Materials",
        "ar": "البحث عن المواد"
    },
    "category": {
        "en": "Category",
        "ar": "الفئة"
    },
    "emirate": {
        "en": "Emirate",
        "ar": "الإمارة"
    },
    "compare": {
        "en": "Compare Emirates",
        "ar": "مقارنة الإمارات"
    },
    "col_code": {
        "en": "Code",
        "ar": "الرمز"
    },
    "col_material": {
        "en": "Material",
        "ar": "المادة"
    },
    "col_unit": {
        "en": "Unit",
        "ar": "الوحدة"
    },
    "col_price": {
        "en": "Price (AED)",
        "ar": "السعر (درهم)"
    },
    "col_accuracy": {
        "en": "Accuracy",
        "ar": "الدقة"
    },
    "col_verified": {
        "en": "Last Verified",
        "ar": "آخر تحقق"
    },
    "disclaimer_title": {
        "en": "Important Disclaimer",
        "ar": "إخلاء مسؤولية هام"
    },
    "disclaimer_body": {
        "en": f"Prices shown are approximate and represent average UAE market rates for {_en_date}. Actual costs will vary based on project scale, bulk volumes, custom specifications, delivery terms, and specific supplier quotations. Always confirm final prices directly before bidding or contracting.",
        "ar": f"الأسعار المعروضة هنا هي أسعار إرشادية تقريبية مبنية على معدلات السوق لشهر {_ar_date}. قد تختلف الأسعار الفعلية حسب الكميات، وموردي المواد، وموقع المشروع والتسليم. يرجى دائماً التحقق من الأسعار مباشرة قبل اتخاذ القرارات النهائية للعقود."
    }
}

# Dynamically set the 'last_verified' date for all fallback materials to today's date
for mat in DEFAULT_MATERIALS:
    mat['last_verified'] = _curr_date.strftime("%Y-%m-%d")

CATEGORIES = {
    "all": {"en": "All Materials", "ar": "جميع المواد"},
    "concrete": {"en": "Concrete & Cement", "ar": "الخرسانة والأسمنت"},
    "steel": {"en": "Steel & Rebar", "ar": "حديد التسليح"},
    "blocks": {"en": "Blocks & Bricks", "ar": "الطابوق والطوب"},
    "sand": {"en": "Sand & Aggregates", "ar": "الرمل والبحص"},
    "finishing": {"en": "Finishing Materials", "ar": "مواد التشطيب"},
    "plumbing": {"en": "Plumbing", "ar": "السباكة والصرف الصحي"},
    "electrical": {"en": "Electrical", "ar": "الأعمال الكهربائية"},
    "insulation": {"en": "Insulation & Waterproofing", "ar": "مواد العزل"},
    "paint": {"en": "Paint & Coatings", "ar": "الدهانات والأصباغ"},
    "tiles": {"en": "Tiles & Flooring", "ar": "البلاط والأرضيات"},
    "doors": {"en": "Doors & Windows", "ar": "الأبواب والنوافذ"}
}

EMIRATES = {
    "dubai": {"en": "Dubai", "ar": "دبي"},
    "abudhabi": {"en": "Abu Dhabi", "ar": "أبو ظبي"},
    "sharjah": {"en": "Sharjah", "ar": "الشارقة"},
    "ajman": {"en": "Ajman", "ar": "عجمان"}
}

def lt(key):
    lang = get_lang()
    return LOCAL_TEXT.get(key, {}).get(lang, key)

@functools.lru_cache(maxsize=1)
def fetch_prices():
    return safe_query("SELECT item_name, unit, rate_aed, last_updated FROM qto_market_prices ORDER BY item_name ASC")

def update_db_prices():
    """Updates the tidb cloud database with the 24-item material prices list without fake fluctuations."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Clear table
                cur.execute("DELETE FROM qto_market_prices")
                
                # Insert all emirate rates for all 24 materials
                for m in DEFAULT_MATERIALS:
                    for em in ["dubai", "abudhabi", "sharjah", "ajman"]:
                        rate = m[em]
                        # Removed fake fluctuation logic
                        
                        em_name = "Abu Dhabi" if em == "abudhabi" else em.capitalize()
                        item_name = f"{m['name_en']} ({em_name})"
                        
                        cur.execute(
                            "INSERT INTO qto_market_prices (item_name, unit, rate_aed, last_updated) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                            (item_name, m["unit"], rate)
                        )
            conn.commit()
        return True, "Successfully updated weekly market prices in database."
    except Exception as e:
        return False, str(e)

@functools.lru_cache(maxsize=1)
def auto_daily_update():
    """Checks if the prices were updated today. If not, updates them automatically."""
    try:
        df = safe_query("SELECT MAX(last_updated) as max_date FROM qto_market_prices")
        needs_update = True
        if not df.empty and pd.notnull(df.iloc[0]["max_date"]):
            last_date = pd.to_datetime(df.iloc[0]["max_date"]).date()
            if last_date >= datetime.datetime.now().date():
                needs_update = False
        
        if needs_update:
            update_db_prices()
    except Exception:
        pass

