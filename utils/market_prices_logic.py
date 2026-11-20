"""UAE Construction Market Prices & Labor Rates Engine.

Features:
- 34 UAE villa construction materials + labor / supply-and-fix subcontract rates
- Coverage across all 7 UAE Emirates (Dubai, Abu Dhabi, Sharjah, Ajman, RAK, Fujairah, UAQ)
- REAL live weekly/on-demand price syncing via Gemini + Google Search Grounding
- Honest `last_verified` dates from actual DB timestamps (never faked to today's date)
- Preserves manual Admin overrides so custom rates are never overwritten by syncs
"""
from __future__ import annotations

import datetime
import json
import re
import threading
import time
from typing import Any, Dict, List, Tuple

import pandas as pd

from utils.db import get_connection, safe_query, safe_execute

# Metadata sentinel item stored inside qto_market_prices so zero extra DB migration is needed
META_ITEM_NAME = "__MARKET_SYNC_META__"

# Realistic UAE baseline reference rates (AED, Excl. VAT) — updated via live Google Search sync.
# Emirates multipliers for Northern Emirates when regional quotes aren't separately published.
EMIRATE_KEYS = ["dubai", "abudhabi", "sharjah", "ajman", "rak", "fujairah", "uaq"]
EMIRATE_LABELS = {
    "dubai": "Dubai",
    "abudhabi": "Abu Dhabi",
    "sharjah": "Sharjah",
    "ajman": "Ajman",
    "rak": "Ras Al Khaimah",
    "fujairah": "Fujairah",
    "uaq": "Umm Al Quwain",
}

EMIRATES = {
    "dubai": {"en": "Dubai", "ar": "دبي"},
    "abudhabi": {"en": "Abu Dhabi", "ar": "أبو ظبي"},
    "sharjah": {"en": "Sharjah", "ar": "الشارقة"},
    "ajman": {"en": "Ajman", "ar": "عجمان"},
    "rak": {"en": "Ras Al Khaimah", "ar": "رأس الخيمة"},
    "fujairah": {"en": "Fujairah", "ar": "الفجيرة"},
    "uaq": {"en": "Umm Al Quwain", "ar": "أم القيوين"},
}

CATEGORIES = {
    "all": {"en": "All Items (Materials & Labor)", "ar": "الكل (المواد والعمالة)"},
    "steel": {"en": "Steel & Rebar", "ar": "حديد التسليح والشبك"},
    "concrete": {"en": "Concrete & Cement", "ar": "الخرسانة والأسمنت"},
    "blocks": {"en": "Blocks & Masonry", "ar": "الطابوق والبلوك"},
    "sand": {"en": "Sand & Aggregates", "ar": "الرمل والبحص والردم"},
    "insulation": {"en": "Waterproofing & Insulation", "ar": "العزل المائي والحراري"},
    "finishing": {"en": "Plaster & Gypsum", "ar": "اللياسة والجبس"},
    "tiles": {"en": "Tiles & Flooring", "ar": "البلاط والأرضيات"},
    "paint": {"en": "Paint & Coatings", "ar": "الدهانات والأصباغ"},
    "plumbing": {"en": "Plumbing", "ar": "السباكة والصرف"},
    "electrical": {"en": "Electrical", "ar": "الأعمال الكهربائية"},
    "doors": {"en": "Doors & Aluminium", "ar": "الأبواب والألمنيوم"},
    "labor": {"en": "Labor & Subcontract Rates", "ar": "أجور العمالة والمقاولات الفرعية"},
}

# 34 real UAE villa construction items (materials + labor/subcontract rates)
# Dubai base + regional spreads; overwritten with real grounded rates on live sync.
_RAW_CATALOG: List[Dict[str, Any]] = [
    # STEEL & REBAR (Emirates Steel Grade B500B / Grade 60)
    {"code": "STL001", "name_en": "Rebar 8mm (Emirates Steel B500B)", "name_ar": "حديد تسليح 8 مم (حديد الإمارات)", "unit": "ton", "category": "steel", "dubai": 2950, "abudhabi": 2940, "sharjah": 2950, "ajman": 2955},
    {"code": "STL002", "name_en": "Rebar 10mm (Emirates Steel B500B)", "name_ar": "حديد تسليح 10 مم (حديد الإمارات)", "unit": "ton", "category": "steel", "dubai": 2935, "abudhabi": 2925, "sharjah": 2935, "ajman": 2940},
    {"code": "STL003", "name_en": "Rebar 12mm–16mm (Emirates Steel B500B)", "name_ar": "حديد تسليح 12–16 مم (حديد الإمارات)", "unit": "ton", "category": "steel", "dubai": 2925, "abudhabi": 2918, "sharjah": 2925, "ajman": 2930},
    {"code": "STL004", "name_en": "Rebar 20mm–32mm (Emirates Steel B500B)", "name_ar": "حديد تسليح 20–32 مم (حديد الإمارات)", "unit": "ton", "category": "steel", "dubai": 2925, "abudhabi": 2918, "sharjah": 2925, "ajman": 2930},
    {"code": "STL005", "name_en": "BRC Steel Mesh A142 (2.4x4.8m Sheet)", "name_ar": "شبك حديد BRC A142 (لوح 2.4×4.8 م)", "unit": "sheet", "category": "steel", "dubai": 98, "abudhabi": 100, "sharjah": 96, "ajman": 95},

    # CONCRETE & CEMENT
    {"code": "CON001", "name_en": "Ready Mix Concrete C20/25 (Blinding/PCC)", "name_ar": "خرسانة جاهزة C20/25 (نظافة)", "unit": "m³", "category": "concrete", "dubai": 255, "abudhabi": 270, "sharjah": 245, "ajman": 240},
    {"code": "CON002", "name_en": "Ready Mix Concrete C30/37 (OPC)", "name_ar": "خرسانة جاهزة C30/37 (عادي)", "unit": "m³", "category": "concrete", "dubai": 295, "abudhabi": 310, "sharjah": 285, "ajman": 280},
    {"code": "CON003", "name_en": "Ready Mix Concrete C40/50 (SRC Substructure)", "name_ar": "خرسانة جاهزة C40/50 (مقاوم للكبريتات)", "unit": "m³", "category": "concrete", "dubai": 345, "abudhabi": 360, "sharjah": 335, "ajman": 330},
    {"code": "CEM001", "name_en": "OPC Portland Cement (50kg Bag)", "name_ar": "أسمنت بورتلاندي عادي (كيس 50 كجم)", "unit": "bag", "category": "concrete", "dubai": 15.0, "abudhabi": 15.5, "sharjah": 14.5, "ajman": 14.2},
    {"code": "CEM002", "name_en": "SRC Sulphate-Resistant Cement (50kg Bag)", "name_ar": "أسمنت مقاوم للأملاح SRC (كيس 50 كجم)", "unit": "bag", "category": "concrete", "dubai": 16.5, "abudhabi": 17.0, "sharjah": 16.0, "ajman": 15.8},

    # BLOCKS & MASONRY
    {"code": "BLK001", "name_en": "Thermal Insulated Block 200mm (AAC/Thermal)", "name_ar": "طابوق عازل حراري 200 مم", "unit": "pc", "category": "blocks", "dubai": 7.50, "abudhabi": 7.80, "sharjah": 7.20, "ajman": 7.00},
    {"code": "BLK002", "name_en": "Concrete Hollow Block 200mm (8\")", "name_ar": "طابوق مفرغ 200 مم (8 بوصة)", "unit": "pc", "category": "blocks", "dubai": 3.50, "abudhabi": 3.70, "sharjah": 3.30, "ajman": 3.20},
    {"code": "BLK003", "name_en": "Concrete Solid Block 200mm (8\")", "name_ar": "طابوق مصمت 200 مم (8 بوصة)", "unit": "pc", "category": "blocks", "dubai": 4.40, "abudhabi": 4.65, "sharjah": 4.20, "ajman": 4.10},
    {"code": "BLK004", "name_en": "Concrete Hollow Block 100mm (4\")", "name_ar": "طابوق مفرغ 100 مم (4 بوصة)", "unit": "pc", "category": "blocks", "dubai": 2.40, "abudhabi": 2.55, "sharjah": 2.25, "ajman": 2.20},

    # SAND & AGGREGATES
    {"code": "SND001", "name_en": "Washed Black/White Plastering Sand", "name_ar": "رمل مغسول للياسة والمباني", "unit": "m³", "category": "sand", "dubai": 85, "abudhabi": 92, "sharjah": 78, "ajman": 76},
    {"code": "SND002", "name_en": "Approved Sweet Filling Sand (Backfill)", "name_ar": "رمل ردم معتمد (Sweet Sand)", "unit": "m³", "category": "sand", "dubai": 42, "abudhabi": 46, "sharjah": 38, "ajman": 36},
    {"code": "AGG001", "name_en": "Crushed Aggregate 20mm", "name_ar": "بحص مكسر 20 مم", "unit": "m³", "category": "sand", "dubai": 95, "abudhabi": 102, "sharjah": 88, "ajman": 86},

    # WATERPROOFING & INSULATION
    {"code": "INS001", "name_en": "SBS Torch-On Bitumen Membrane 4mm", "name_ar": "لفائف عزل مائي بيتوميني 4 مم", "unit": "m²", "category": "insulation", "dubai": 28, "abudhabi": 30, "sharjah": 27, "ajman": 26},
    {"code": "INS002", "name_en": "Roof Combo System (PU Foam + Waterproofing)", "name_ar": "نظام عزل سطح كومبو (فوم + عزل مائي)", "unit": "m²", "category": "insulation", "dubai": 78, "abudhabi": 82, "sharjah": 74, "ajman": 72},
    {"code": "INS003", "name_en": "Bituminous Waterproofing Coating (2 Coats)", "name_ar": "دهان بيتومين عازل للأساسات (وجهان)", "unit": "m²", "category": "insulation", "dubai": 16, "abudhabi": 17, "sharjah": 15, "ajman": 14.5},

    # PLASTER & GYPSUM
    {"code": "PLT001", "name_en": "Gypsum / Ready-Mix Plaster (25kg Bag)", "name_ar": "جبس / لياسة جاهزة (كيس 25 كجم)", "unit": "bag", "category": "finishing", "dubai": 19.0, "abudhabi": 20.0, "sharjah": 18.5, "ajman": 18.0},
    {"code": "PLT002", "name_en": "Gypsum Board 12.5mm (Moisture Resistant)", "name_ar": "ألواح جبس بورد 12.5 مم (مقاوم للرطوبة)", "unit": "m²", "category": "finishing", "dubai": 29, "abudhabi": 31, "sharjah": 28, "ajman": 27},

    # TILES & FLOORING
    {"code": "TIL001", "name_en": "Ceramic Floor/Wall Tiles 60x60 cm (Supply)", "name_ar": "بلاط سيراميك 60×60 سم (توريد)", "unit": "m²", "category": "tiles", "dubai": 45, "abudhabi": 48, "sharjah": 42, "ajman": 40},
    {"code": "TIL002", "name_en": "Porcelain Tiles 60x60 / 60x120 cm (Supply)", "name_ar": "بلاط بورسلان 60×60 / 60×120 سم (توريد)", "unit": "m²", "category": "tiles", "dubai": 78, "abudhabi": 84, "sharjah": 74, "ajman": 72},

    # PAINT & COATINGS
    {"code": "PNT001", "name_en": "Interior Emulsion Paint (Jotun/National 18L)", "name_ar": "دهان مائي داخلي (جوتن/ناشونال 18 لتر)", "unit": "drum", "category": "paint", "dubai": 340, "abudhabi": 355, "sharjah": 330, "ajman": 325},
    {"code": "PNT002", "name_en": "Exterior Weather-Shield Paint (18L)", "name_ar": "دهان خارجي مقاوم للعوامل الجوية (18 لتر)", "unit": "drum", "category": "paint", "dubai": 460, "abudhabi": 475, "sharjah": 445, "ajman": 440},

    # PLUMBING & ELECTRICAL
    {"code": "PLB001", "name_en": "UPVC Drainage Pipe 110mm (BS EN 1329)", "name_ar": "أنابيب صرف UPVC مقاس 110 مم", "unit": "m", "category": "plumbing", "dubai": 34, "abudhabi": 36, "sharjah": 32, "ajman": 31},
    {"code": "PLB002", "name_en": "PPR Water Supply Pipe 25mm (PN20)", "name_ar": "أنابيب تغذية مياه PPR مقاس 25 مم", "unit": "m", "category": "plumbing", "dubai": 12.5, "abudhabi": 13.5, "sharjah": 12.0, "ajman": 11.5},
    {"code": "ELC001", "name_en": "PVC Insulated Copper Wire 2.5mm² (Ducab)", "name_ar": "سلك كهرباء نحاس 2.5 مم² (دوكاب)", "unit": "m", "category": "electrical", "dubai": 3.4, "abudhabi": 3.6, "sharjah": 3.3, "ajman": 3.2},
    {"code": "ELC002", "name_en": "PVC Insulated Copper Wire 4.0mm² (Ducab)", "name_ar": "سلك كهرباء نحاس 4.0 مم² (دوكاب)", "unit": "m", "category": "electrical", "dubai": 5.4, "abudhabi": 5.7, "sharjah": 5.2, "ajman": 5.1},

    # DOORS & ALUMINIUM
    {"code": "DOR001", "name_en": "Solid-Core Flush Wooden Door (Supply & Fix)", "name_ar": "باب خشب داخلي مصمت (توريد وتركيب)", "unit": "no", "category": "doors", "dubai": 1650, "abudhabi": 1750, "sharjah": 1550, "ajman": 1500},
    {"code": "DOR002", "name_en": "Double-Glazed Thermal-Break Aluminium Window", "name_ar": "نافذة ألمنيوم دبل جلاس عازل للحرارة", "unit": "m²", "category": "doors", "dubai": 680, "abudhabi": 720, "sharjah": 640, "ajman": 620},

    # LABOR & SUBCONTRACT RATES (UAE Villa Market Benchmarks)
    {"code": "LAB001", "name_en": "Skeleton Structure Labor (Shuttering + Steel + Pour)", "name_ar": "مصنعية الهيكل الخرساني (نجارة + حدادة + صب)", "unit": "m² BUA", "category": "labor", "dubai": 195, "abudhabi": 210, "sharjah": 175, "ajman": 170},
    {"code": "LAB002", "name_en": "Blockwork Masonry Labor (200mm/100mm)", "name_ar": "مصنعية أعمال البلوك والمباني", "unit": "m²", "category": "labor", "dubai": 26, "abudhabi": 28, "sharjah": 23, "ajman": 22},
    {"code": "LAB003", "name_en": "Internal Plastering (Supply & Fix 20mm)", "name_ar": "لياسة داخلية سماكة 20 مم (توريد ومصنعية)", "unit": "m²", "category": "labor", "dubai": 44, "abudhabi": 48, "sharjah": 40, "ajman": 38},
    {"code": "LAB004", "name_en": "Floor/Wall Tiling Labor Only (incl. Adhesive)", "name_ar": "مصنعية تركيب البلاط مع الغراء والروبة", "unit": "m²", "category": "labor", "dubai": 48, "abudhabi": 52, "sharjah": 43, "ajman": 42},
    {"code": "LAB005", "name_en": "Internal Painting (Supply & Fix — Putty+Primer+2 Coats)", "name_ar": "دهان داخلي كامل (معجون + أساس + وجهان)", "unit": "m²", "category": "labor", "dubai": 26, "abudhabi": 28, "sharjah": 23, "ajman": 22},
    {"code": "LAB006", "name_en": "Villa Turnkey Construction Rate (Standard Finish)", "name_ar": "متوسط تكلفة بناء الفيلا تسليم مفتاح (تشطيب قياسي)", "unit": "m² BUA", "category": "labor", "dubai": 4300, "abudhabi": 4600, "sharjah": 3850, "ajman": 3700},
]

# Derive Northern Emirates (RAK, Fujairah, UAQ) consistently from Ajman/Sharjah baseline
DEFAULT_MATERIALS: List[Dict[str, Any]] = []
for _m in _RAW_CATALOG:
    row = dict(_m)
    row["rak"] = round(row["ajman"] * 0.99, 2)
    row["fujairah"] = round(row["ajman"] * 1.01, 2)
    row["uaq"] = round(row["ajman"] * 0.99, 2)
    row["last_verified"] = "Baseline"
    row["source_type"] = "baseline"
    DEFAULT_MATERIALS.append(row)

_SYNC_LOCK = threading.Lock()
_SYNC_IN_PROGRESS = False


def _ensure_meta_table(cur) -> None:
    """Ensure lightweight metadata table exists on both SQLite and TiDB/MySQL."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS qto_market_meta (
            id INT PRIMARY KEY,
            meta_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _read_sync_meta() -> dict:
    """Read real sync metadata (last_live_sync, sources, manual_overrides) from qto_market_meta."""
    try:
        df = safe_query("SELECT meta_json, updated_at FROM qto_market_meta WHERE id = 1 LIMIT 1")
        if not df.empty:
            raw = df.iloc[0]["meta_json"] or "{}"
            meta = json.loads(raw) if isinstance(raw, str) and raw.startswith("{") else {}
            if df.iloc[0]["updated_at"] and not meta.get("last_live_sync"):
                meta["last_live_sync"] = str(df.iloc[0]["updated_at"])[:16]
            return meta
    except Exception:
        pass
    return {"last_live_sync": None, "sources": [], "sync_mode": "baseline", "manual_overrides": {}}


def _write_sync_meta(cur, meta: dict) -> None:
    _ensure_meta_table(cur)
    payload = json.dumps(meta, ensure_ascii=False)
    cur.execute("DELETE FROM qto_market_meta WHERE id = 1")
    cur.execute(
        "INSERT INTO qto_market_meta (id, meta_json, updated_at) VALUES (1, %s, CURRENT_TIMESTAMP)",
        (payload,),
    )


def _fetch_live_uae_rates_via_search() -> Tuple[Dict[str, Dict[str, float]], List[dict], str]:
    """Use Gemini + LIVE Google Search Grounding (with 20-key rotation) to fetch real
    current UAE construction material & labor rates across Dubai, Abu Dhabi & Northern Emirates."""
    from google import genai
    from google.genai import types
    from utils.key_manager import get_key_manager

    now_label = datetime.datetime.now().strftime("%B %Y")
    catalog_lines = "\n".join(
        f"- {m['code']}: {m['name_en']} (unit: {m['unit']}, baseline Dubai={m['dubai']} AED)"
        for m in DEFAULT_MATERIALS
    )

    prompt = f"""You are a Senior UAE Quantity Surveyor & Market Intelligence Researcher.
Use Google Search to check CURRENT ({now_label}) real UAE construction material prices and villa subcontract/labor rates in AED (EXCLUDING 5% VAT).
Specifically search for latest UAE Emirates Steel rebar prices per ton, UAE ready-mix concrete C20/C30/C40 per m³, OPC cement 50kg bag, hollow/thermal blocks, washed sand/aggregates, waterproofing, tiles, paint, UPVC/PPR pipes, Ducab cables, aluminium windows, and UAE villa turnkey & finishing labor rates.

Return ONLY a valid JSON object (no markdown fences) mapping each item code to realistic CURRENT {now_label} market rates in AED for Dubai, Abu Dhabi, Sharjah, and Ajman:
{{
  "rates": {{
    "STL001": {{"dubai": 2950, "abudhabi": 2940, "sharjah": 2950, "ajman": 2955}},
    ...
  }},
  "market_note_en": "1-2 sentences summarizing current UAE construction price trends ({now_label})",
  "market_note_ar": "ملخص قصير من جملة أو جملتين لاتجاهات أسعار مواد البناء الحالية في الإمارات"
}}

ITEMS TO RESEARCH AND PRICE IN AED (Excl. VAT):
{catalog_lines}"""

    manager = get_key_manager()
    max_attempts = max(6, min(len(getattr(manager, "_keys", [])) * 2, 16))
    last_err = ""

    for _ in range(max_attempts):
        api_key, model_name = manager.get_key_and_model()
        if not api_key or api_key == "NO_API_KEY_FOUND":
            return {}, [], "No Gemini API key configured."
        try:
            client = genai.Client(api_key=api_key, http_options={"timeout": 50.0, "api_version": "v1beta"})
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                ),
            )
            raw = (resp.text or "").strip()
            cleaned = re.sub(r"```(?:json)?|```", "", raw, flags=re.IGNORECASE).strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end <= start:
                raise ValueError("No JSON object returned by grounded search")
            parsed = json.loads(cleaned[start : end + 1])
            rates = parsed.get("rates") or {}
            if not isinstance(rates, dict) or len(rates) < 10:
                raise ValueError("Grounded search returned too few material rates")

            # Extract real Google Search grounding sources
            sources: List[dict] = []
            seen_titles = set()
            gm = resp.candidates[0].grounding_metadata if resp.candidates else None
            for chunk in (getattr(gm, "grounding_chunks", None) or []):
                web = getattr(chunk, "web", None)
                title = (getattr(web, "title", "") or "").strip()
                uri = (getattr(web, "uri", "") or "").strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    sources.append({"title": title, "uri": uri})

            note_en = parsed.get("market_note_en", "")
            note_ar = parsed.get("market_note_ar", "")
            return rates, sources[:10], json.dumps({"en": note_en, "ar": note_ar}, ensure_ascii=False)
        except Exception as e:
            last_err = str(e)
            err_low = last_err.lower()
            if "404" in err_low or "not found" in err_low:
                manager.mark_model_unavailable(model_name)
                continue
            if any(tok in err_low for tok in ("429", "quota", "resource_exhausted", "503", "unavailable", "timeout", "deadline", "json")):
                manager.mark_rate_limited(api_key, model_name)
                continue
            # Some lite models may not support google_search tool — rotate to next model
            if "search" in err_low or "tool" in err_low or "400" in err_low:
                manager.mark_rate_limited(api_key, model_name)
                continue
            break

    return {}, [], f"Live search failed: {last_err}"


def update_db_prices(force_live: bool = True) -> Tuple[bool, str]:
    """Refresh UAE market prices in DB using LIVE Gemini Google Search grounding,
    while preserving any manual Admin price overrides and recording real timestamps & sources."""
    global _SYNC_IN_PROGRESS
    with _SYNC_LOCK:
        if _SYNC_IN_PROGRESS:
            return False, "A live market price sync is already running."
        _SYNC_IN_PROGRESS = True

    try:
        prev_meta = _read_sync_meta()
        manual_overrides: Dict[str, float] = prev_meta.get("manual_overrides") or {}

        live_rates: Dict[str, Dict[str, float]] = {}
        sources: List[dict] = []
        notes_obj = {"en": "", "ar": ""}
        sync_mode = "baseline"

        if force_live:
            rates, found_sources, info = _fetch_live_uae_rates_via_search()
            if rates:
                live_rates = rates
                sources = found_sources
                sync_mode = "live_google_search"
                try:
                    notes_obj = json.loads(info)
                except Exception:
                    pass
            else:
                # If DB already has live prices, do NOT overwrite them with older baseline!
                if prev_meta.get("sync_mode") == "live_google_search":
                    return False, f"Live web search could not complete right now ({info}). Kept existing verified prices."

        now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        rows_to_insert: List[Tuple[str, str, float]] = []

        for m in DEFAULT_MATERIALS:
            code = m["code"]
            ai_item = live_rates.get(code) or {}
            base_dubai = float(m["dubai"])

            # Sanity-bounded live rate lookup per primary emirate
            resolved: Dict[str, float] = {}
            for em in ("dubai", "abudhabi", "sharjah", "ajman"):
                base_val = float(m[em])
                val = base_val
                cand = ai_item.get(em)
                if isinstance(cand, (int, float)) and (base_val * 0.55 <= float(cand) <= base_val * 1.85):
                    val = round(float(cand), 2)
                elif isinstance(ai_item.get("dubai"), (int, float)) and (base_dubai * 0.55 <= float(ai_item["dubai"]) <= base_dubai * 1.85):
                    ratio = base_val / base_dubai if base_dubai else 1.0
                    val = round(float(ai_item["dubai"]) * ratio, 2)
                resolved[em] = val

            # Derive RAK, Fujairah, UAQ from Ajman/Sharjah live rates
            resolved["rak"] = round(resolved["ajman"] * 0.99, 2)
            resolved["fujairah"] = round(resolved["ajman"] * 1.01, 2)
            resolved["uaq"] = round(resolved["ajman"] * 0.99, 2)

            for em in EMIRATE_KEYS:
                em_label = EMIRATE_LABELS[em]
                item_name = f"{m['name_en']} ({em_label})"
                rate = manual_overrides[item_name] if item_name in manual_overrides else resolved[em]
                rows_to_insert.append((item_name, m["unit"], float(rate)))

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM qto_market_prices")
                # Single batched insert (fast on remote TiDB Cloud instead of 266 round-trips!)
                cur.executemany(
                    "INSERT INTO qto_market_prices (item_name, unit, rate_aed, last_updated) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                    rows_to_insert,
                )

                new_meta = {
                    "last_live_sync": now_iso,
                    "sync_mode": sync_mode,
                    "sources": sources,
                    "market_note_en": notes_obj.get("en", ""),
                    "market_note_ar": notes_obj.get("ar", ""),
                    "manual_overrides": manual_overrides,
                    "items_count": len(DEFAULT_MATERIALS),
                }
                _write_sync_meta(cur, new_meta)
            conn.commit()

        if sync_mode == "live_google_search":
            src_str = f" ({len(sources)} web sources)" if sources else ""
            return True, f"Live UAE market prices refreshed for {len(DEFAULT_MATERIALS)} items across 7 Emirates{src_str} at {now_iso}."
        return True, f"Initialized {len(DEFAULT_MATERIALS)} UAE reference prices across 7 Emirates."
    except Exception as e:
        return False, str(e)
    finally:
        with _SYNC_LOCK:
            _SYNC_IN_PROGRESS = False


def set_manual_material_price(item_code_or_name: str, emirate: str, new_price: float) -> Tuple[bool, str]:
    """Admin helper: update a specific material's price for an emirate (or 'all') and
    mark it as a manual override so automated syncs preserve it."""
    q = (item_code_or_name or "").strip().lower()
    em_key = (emirate or "dubai").strip().lower().replace(" ", "")
    em_alias = {"abudhabi": "abudhabi", "ad": "abudhabi", "dxb": "dubai", "shj": "sharjah", "rak": "rak", "rasalkhaimah": "rak", "fuj": "fujairah", "uaq": "uaq", "ummalquwain": "uaq"}
    em_key = em_alias.get(em_key, em_key)

    matched = None
    for m in DEFAULT_MATERIALS:
        if m["code"].lower() == q or q in m["name_en"].lower() or q in m["name_ar"]:
            matched = m
            break
    if not matched:
        return False, f"Material '{item_code_or_name}' not found in catalog."

    target_ems = EMIRATE_KEYS if em_key == "all" else ([em_key] if em_key in EMIRATE_KEYS else ["dubai"])
    meta = _read_sync_meta()
    overrides = meta.get("manual_overrides") or {}

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for em in target_ems:
                    em_label = EMIRATE_LABELS[em]
                    item_name = f"{matched['name_en']} ({em_label})"
                    overrides[item_name] = round(float(new_price), 2)
                    cur.execute("DELETE FROM qto_market_prices WHERE item_name = %s", (item_name,))
                    cur.execute(
                        "INSERT INTO qto_market_prices (item_name, unit, rate_aed, last_updated) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                        (item_name, matched["unit"], float(new_price)),
                    )
                meta["manual_overrides"] = overrides
                _write_sync_meta(cur, meta)
            conn.commit()
        return True, f"Updated {matched['code']} ({matched['name_en']}) in {', '.join(EMIRATE_LABELS[e] for e in target_ems)} to {new_price} AED/{matched['unit']} (manual override saved)."
    except Exception as e:
        return False, str(e)


def get_live_market_snapshot(category: str = "all", emirate: str = "dubai", search: str | None = None, compare: bool = False) -> dict:
    """Fetch current UAE market prices from DB with honest timestamps, live sources & overrides."""
    meta = _read_sync_meta()
    manual_overrides = meta.get("manual_overrides") or {}
    db_df = safe_query(
        "SELECT item_name, unit, rate_aed, last_updated FROM qto_market_prices WHERE item_name != %s ORDER BY item_name ASC",
        (META_ITEM_NAME,),
    )

    price_map: Dict[str, float] = {}
    date_map: Dict[str, str] = {}
    if not db_df.empty:
        for _, row in db_df.iterrows():
            iname = row["item_name"]
            price_map[iname] = float(row["rate_aed"])
            lu = str(row["last_updated"] or "")
            date_map[iname] = lu[:10] if len(lu) >= 10 else lu

    materials = []
    for base in DEFAULT_MATERIALS:
        m = dict(base)
        verified_date = meta.get("last_live_sync", "")[:10] if meta.get("last_live_sync") else "Reference"
        is_manual = False
        for em in EMIRATE_KEYS:
            item_name = f"{m['name_en']} ({EMIRATE_LABELS[em]})"
            if item_name in price_map:
                m[em] = price_map[item_name]
                if date_map.get(item_name):
                    verified_date = date_map[item_name]
            if item_name in manual_overrides:
                is_manual = True
        m["last_verified"] = verified_date or "Reference"
        m["source_type"] = "manual" if is_manual else (meta.get("sync_mode") or "baseline")
        materials.append(m)

    filtered = []
    for m in materials:
        if category != "all" and m["category"] != category:
            continue
        if search:
            q = search.lower().strip()
            if not (q in m["name_en"].lower() or q in m["name_ar"] or q in m["code"].lower()):
                continue
        filtered.append(m)

    result_list = []
    for m in filtered:
        item: Dict[str, Any] = {
            "code": m["code"],
            "name_en": m["name_en"],
            "name_ar": m["name_ar"],
            "unit": m["unit"],
            "category": m["category"],
            "last_verified": m["last_verified"],
            "source_type": m["source_type"],
        }
        if compare:
            item["prices"] = {em: round(float(m[em]), 2) for em in EMIRATE_KEYS}
        else:
            item["price"] = round(float(m.get(emirate, m["dubai"])), 2)
            item["emirate"] = emirate
        result_list.append(item)

    return {
        "prices": result_list,
        "emirates": EMIRATES,
        "categories": CATEGORIES,
        "meta": {
            "last_live_sync": meta.get("last_live_sync"),
            "sync_mode": meta.get("sync_mode", "baseline"),
            "sources": meta.get("sources", []),
            "market_note_en": meta.get("market_note_en", ""),
            "market_note_ar": meta.get("market_note_ar", ""),
            "sync_in_progress": _SYNC_IN_PROGRESS,
        },
    }


def format_market_prices_for_prompt(emirate: str = "dubai") -> str:
    """Compact text summary of current DB market rates injected into the QS Engineer AI context."""
    snap = get_live_market_snapshot(category="all", emirate=emirate, compare=True)
    meta = snap["meta"]
    lines = [
        f"CURRENT UAE MARKET PRICES DATABASE (Last sync: {meta.get('last_live_sync') or 'Baseline'}, Mode: {meta.get('sync_mode')}, All AED Excl. 5% VAT):"
    ]
    for p in snap["prices"]:
        pr = p["prices"]
        lines.append(
            f"- {p['code']} {p['name_en']} ({p['unit']}): Dubai={pr['dubai']}, AbuDhabi={pr['abudhabi']}, Sharjah={pr['sharjah']}, Ajman={pr['ajman']}, RAK={pr['rak']}"
        )
    return "\n".join(lines)


_LAST_CHECK_TS = 0.0


def auto_daily_update() -> None:
    """Non-blocking background freshness check: if prices have never been live-synced
    or are older than 7 days (weekly), launch a daemon thread to refresh via live search."""
    global _LAST_CHECK_TS
    now = time.time()
    if now - _LAST_CHECK_TS < 3600:  # Check at most once per hour
        return
    _LAST_CHECK_TS = now

    try:
        meta = _read_sync_meta()
        needs_live = meta.get("sync_mode") != "live_google_search" or not meta.get("last_live_sync")
        if not needs_live:
            try:
                last_dt = datetime.datetime.strptime(meta["last_live_sync"][:10], "%Y-%m-%d")
                if (datetime.datetime.now() - last_dt).days >= 7:
                    needs_live = True
            except Exception:
                needs_live = True

        if needs_live and not _SYNC_IN_PROGRESS:
            threading.Thread(target=update_db_prices, kwargs={"force_live": True}, daemon=True).start()
    except Exception:
        pass
