"""
STEP 2 — Classify Pages
Hybrid classifier:
  1. Deterministic title/keyword/content scoring with word boundaries, boilerplate
     stripping, floor-plan vs elevation/section disambiguation, and non-takeoff
     sheet rejection (cover sheets, regulations/notes, typical rebar details,
     structural boundary wall sheets, staircase detail sheets).
  2. Concurrent AI Vision fallback (_ai_classify) for pages with SHX vector-stroke
     titles or ambiguous text — including explicit 'unknown' classification for
     non-takeoff sheets.
"""
import os
import io
import re
import json
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from pdf_engine.smart_classifier import classify_all_pages, PAGE_ITEMS_MAP
from pdf_engine.pdf_loader import page_to_pil
from workflow.workflow_state import mark_step_done

# Candidate types per PDF kind — used by the AI-vision refiner
_STRUCT_TYPES = [
    "foundations", "tie_beam", "column_layout", "upper_columns", "neck_columns",
    "columns_1f", "columns_2f", "columns_roof",
    "slab_1st", "slab_2nd", "roof_slab", "unknown",
]
_ARCH_TYPES = [
    "ground_floor_plan", "first_floor_plan", "second_floor_plan",
    "roof_floor_plan", "elevations", "setting_out", "schedules", "unknown",
]

# Repeating consultant title-block disclaimers that poison naive keyword matching
_BOILERPLATE_RE = re.compile(
    r"(?:"
    r"all\s+dimensions\s+are\s+in\s+\w+|"
    r"all\s+windows\s+are\s+double\s+glazed|"
    r"all\s+external\s+walls\s+shown|"
    r"all\s+external\s+roofs|"
    r"all\s+roofing\s+surfaces|"
    r"read\s+in\s+conjunction\s+with|"
    r"structural\s*,?\s*mechanical\s*[&and]+\s*electrical|"
    r"columns\s+are\s+designed\s+for\s+g\+\d|"
    r"f\.?f\.?l\.?\s+finished\s+floor\s+level|"
    r"f\.?s\.?l\.?\s+finished\s+site\s+level|"
    r"s\.?s\.?l\.?\s+structure\s+slab\s+level|"
    r"c\.?l\.?\s+concrete\s+level|"
    r"t\.?l\.?\s+top\s+level|"
    r"r\.?l\.?\s+road\s+level|"
    r"kicker\s+to\s+be\s+cast|"
    r"details\s+for\s+approval\s+before\s+starting"
    r")[^\n]*",
    re.IGNORECASE,
)

# Floor-plan room indicator words (whole words)
_ROOM_WORDS_RE = re.compile(
    r"\b(?:MAJLIS|LIVING|BED\s*ROOM|MASTER\s+BED|KITCHEN|DINING|TOILET|BATH\s*ROOM|"
    r"BATH|DRESSING|MAID|LAUNDRY|PANTRY|STORE|FOYER|HALL|LOBBY|FAMILY\s+HALL|"
    r"POWDER\s+ROOM|GUEST\s+ROOM|PRAYER|BALCONY|TERRACE|W\.?C\.?)\b",
    re.IGNORECASE,
)

# Strict opening mark tokens on architectural floor plans (D1, D2, MD1, W1, W6...)
_PLAN_MARK_RE = re.compile(
    r"(?<![A-Z0-9.])(?:MD|SD|FD|GD|CW|KW|SW|D|W|V)[\-\s]?0*[1-9]\d?(?![A-Z0-9.])",
    re.IGNORECASE,
)

# Level markers that appear on Elevations & Sections (e.g., "01 GROUND FLOOR F.F.L +0.60")
_LEVEL_MARKER_RE = re.compile(
    r"(?:F\.?F\.?L\.?|S\.?S\.?L\.?|T\.?O\.?S\.?|PARAPET\s+LEV\w*|GATE\s+LEVEL|INTERLOCK\s+LEVEL)"
    r"[\s.:=]*[+\-]?\s*\d+\.\d{1,2}",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    if not text:
        return ""
    # Strip AutoCAD formatting prefixes like %%U, \A1;
    cleaned = re.sub(r"%%[A-Za-z]|\\[A-Za-z]\d+;", " ", text)
    cleaned = _BOILERPLATE_RE.sub(" ", cleaned)
    return cleaned


def _has_kw(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def _is_non_takeoff_sheet(raw_text: str, clean_text: str, pdf_type: str) -> tuple[bool, str]:
    """
    Detect cover sheets, green-building regulations, general notes/abbreviations,
    typical rebar details, staircase details, and structural boundary-wall sheets
    so they are cleanly marked 'unknown' instead of corrupting QTO quantities.
    """
    # 1. Very dense prose pages (> 7,000 chars) are always regulations or general notes
    if len(raw_text) > 7000:
        return True, "dense_notes_or_regulations"

    up = clean_text.upper()

    # 2. General notes / regulations / cover / area-summary sheets
    if _has_kw(up, r"\b(?:DUBAI\s+GREEN\s+BUILDING|GREEN\s+BUILDING\s+REGULATIONS|GENERAL\s+NOTES\b|LIST\s+OF\s+DRAWINGS|DRAWING\s+INDEX|DRAWING\s+LIST|ABBREVIATIONS\s+AND\s+SYMBOLS)\b"):
        return True, "notes_or_index"

    if pdf_type == "architectural":
        # Cover / plot data sheet (no rooms, no schedules, has approval / FAR / coverage table)
        if _has_kw(up, r"\b(?:CIVIL\s+DEFENCE\s+APPROVAL|PLOT\s+COVERAGE\s+ALLOWED|FLOOR\s+AREA\s+RATIO\s+ALLOWED)\b"):
            return True, "cover_or_approval_sheet"
        # Area calculation / BUA summary table sheet (NOT a floor plan — no room layout)
        if _has_kw(up, r"\b(?:AREA\s+CALCULATION|BUILT[\s\-]+UP\s+AREA\s+SCHEDULE|PROPOSED\s+VILLA\s+GROUND\s+FLOOR)\b") and len(_ROOM_WORDS_RE.findall(up)) < 3:
            return True, "area_calculation_sheet"
        # Pure stair detail sheets (e.g. "STAIRS DETAILS - SECTION 3-3")
        if _has_kw(up, r"\b(?:STAIRS?\s+DET(?:AILS?|IALS?)|STAIR\s*CASE\s+DET(?:AILS?|IALS?))\b"):
            return True, "stair_details"
        # Boundary wall elevation/section detail sheets (not villa elevations and not setting-out)
        if _has_kw(up, r"\b(?:FRONT|REAR|LEFT|RIGHT)\s+ELEVATION\s+B\.?W\.?\b|\bBOUNDARY\s+WALL\s+(?:FRONT|REAR|SIDE|LEFT|RIGHT)?\s*ELEVATION\b|\bSITE\s+SECTIONS?\b"):
            return True, "boundary_wall_elevation"

    elif pdf_type == "structural":
        # Cover / very sparse title page with no structural layout keywords
        if len(raw_text.strip()) < 650 and not _has_kw(up, r"\b(?:FOOTING|FOUNDATION|TIE\s+BEAM|SLAB|COLUMN|BEAM)\b"):
            return True, "sparse_cover"
        # Structural boundary-wall / fence layout (must NEVER be mixed with villa foundations/tie-beams!)
        if _has_kw(up, r"\b(?:BOUNDARY\s+WALL\s+(?:LAYOUT|DETAIL|SECTION|FOOTING)|TYPICAL\s+IN\s+BOUNDARY\s+WALL|COMPOUND\s+WALL\s+(?:LAYOUT|FOOTING|DETAIL))\b"):
            return True, "structural_boundary_wall"
        # Staircase structural layout/detail sheet (staircase concrete is computed parametrically per level)
        if _has_kw(up, r"\b(?:STAIR\s*CASE\s+(?:LAYOUT|DETAIL|TREAD)|STAIRS?\s+DETAILS?)\b") and not _has_kw(up, r"\b(?:FIRST\s+FLOOR|1ST\s+FLOOR|F\.?FLOOR|ROOF)\s+SLAB\b"):
            return True, "structural_stair_detail"
        # Standard/typical rebar details & notes sheets (no villa layout)
        if _has_kw(up, r"\b(?:TYPICAL\s+ARRANGEMENT\s+OF|TYPICAL\s+RFT\.?\s+DETAIL|TYPICAL\s+DETAIL\s+OF|TYPICAL\s+SLAB\s+DETAIL|SLEEVE\s+THROUGH|SCHEDULE\s+OF\s+PUNCHING\s+SHEAR|COLUMN\s+REACTIONS)\b"):
            return True, "typical_rebar_detail"
        # Legend / abbreviation sheet
        if _has_kw(up, r"\bSETTING\s+OUT\s+POINT\b") and _has_kw(up, r"\bSTRUCT'?L\.?\s+LEVEL\b"):
            return True, "structural_legend"

    return False, ""


def _classify_structural(raw_text: str, clean_text: str) -> dict:
    """High-precision deterministic classifier for UAE structural PDF pages."""
    is_skip, reason = _is_non_takeoff_sheet(raw_text, clean_text, "structural")
    if is_skip:
        return {"detected_type": "unknown", "confidence": "high", "items": [], "reason": reason}

    up = clean_text.upper()

    # 1. Explicit Tie-Beam Layout (must check BEFORE generic "column layout" because
    #    some consultants title the tie-beam plan "TIE BEAM COLUMN LAYOUT" alongside
    #    "TIE BEAM LAYOUT", whereas actual column layouts say "UPTO TIE BEAM" or "TIE BEAM TO ...").
    is_col_level_range = _has_kw(
        up,
        r"\b(?:UP\s*TO\s+TIE\s+BEAM|FOUNDATION\s+TO\s+TIE\s+BEAM|TIE\s+BEAM\s+TO\s+(?:F\.?\s*FLOOR|FIRST|1ST|ROOF))\b",
    )
    if not is_col_level_range and _has_kw(
        up,
        r"\b(?:TIE\s+BEAM\s+(?:LAYOUT|PLAN|SCHEDULE|DETAILS?)|"
        r"SCHEDULE\s+(?:OF|FOR)\s+TIE\s+BEAMS?|GROUND\s+BEAM\s+(?:LAYOUT|PLAN)|"
        r"PLINTH\s+BEAM\s+(?:LAYOUT|PLAN)|T\.?B\.?\s+SCHEDULE)\b",
    ) and not _has_kw(up, r"\b(?:FOOTING\s+AXIS\s+LAYOUT|FOOTING\s+LAYOUT|FOUNDATION\s+(?:LAYOUT|PLAN)|SCHEDULE\s+(?:OF|FOR)\s+FOOTINGS?)\b"):
        return {
            "detected_type": "tie_beam",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["tie_beam"]["extract_items"],
        }

    # 2. Column layouts & schedules (check before roof_slab / foundations because
    #    titles literally say "UPTO TIE BEAM COLUMN LAYOUT" or "F.FLOOR TO ROOF SLAB COLUMN LAYOUT"!)
    is_col_title = _has_kw(
        up,
        r"\b(?:COLUMN\s+AXIS\s+LAYOUT|COLUMNS?\s+LAYOUT|AXIS\s+AND\s+COLUMN\s+LAYOUT|"
        r"COLUMN\s+LOCATION|COLUMNS?\s+PLAN|(?:GROUND|1ST|FIRST|2ND|SECOND|ROOF)\s+FLOOR\s+COLUMNS?|"
        r"FISRT\s+FLOOR\s+COLUMNS?|NECK\s+COLUMNS?)\b",
    )
    is_col_sched = _has_kw(
        up,
        r"\b(?:COLUMN\s+SCHEDULE|COLUMNS?\s+SCHEDULE|SCHEDULE\s+OF\s+COLUMNS?|"
        r"TYPICAL\s+COLUMN\s+SCHEDULE|COL\.?\s*SCH\.?|COLUMNS?\s+DETAIL(?:S)?)\b",
    )

    if is_col_title or is_col_sched:
        # Distinguish specific floor column layouts first
        if _has_kw(up, r"\b(?:UP\s*TO\s+TIE\s+BEAM|FOUNDATION\s+TO\s+TIE\s+BEAM|NECK\s+COL|GROUND\s+FLOOR\s+COL|G\.?F\.?\s+COL)\b"):
            best = "neck_columns"
        elif _has_kw(up, r"\b(?:TIE\s+BEAM\s+TO\s+(?:F\.?\s*FLOOR|FIRST|1ST)|(?:FIRST|1ST|FISRT)\s+FLOOR\s+COL)\b"):
            best = "columns_1f"
        elif _has_kw(up, r"\b(?:(?:F\.?\s*FLOOR|FIRST|1ST)\s*(?:SLAB|FLOOR)?\s*TO\s+(?:2ND|SECOND)|(?:2ND|SECOND)\s+FLOOR\s+COL)\b"):
            best = "columns_2f"
        elif _has_kw(up, r"\b(?:(?:F\.?\s*FLOOR|FIRST|1ST|2ND|SECOND)\s*(?:SLAB|FLOOR)?\s*TO\s+ROOF|ROOF\s+(?:FLOOR\s+)?COL)\b"):
            best = "columns_roof"
        elif is_col_sched:
            best = "upper_columns"
        else:
            best = "column_layout"
        return {
            "detected_type": best,
            "confidence": "high",
            "items": PAGE_ITEMS_MAP.get(best, {}).get("extract_items", []),
        }

    # 3. Foundations / Footings layout & schedule (beats tie_beam if both words appear in notes)
    if _has_kw(
        up,
        r"\b(?:FOOTING\s+AXIS\s+LAYOUT|FOOTING\s+LAYOUT|FOOTINGS?\s+PLAN|"
        r"FOUNDATION\s+(?:LAYOUT|PLAN)|SCHEDULE\s+(?:OF|FOR)\s+FOOTINGS?|"
        r"FOOTING\s+SCHEDULE|FOUNDATION\s+SCHEDULE|ISOLATED\s+FOOTING)\b",
    ):
        return {
            "detected_type": "foundations",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["foundations"]["extract_items"],
        }

    # 4. Slabs (Roof / 2nd / 1st)
    if _has_kw(
        up,
        r"\b(?:ROOF\s+(?:FLOOR\s+)?(?:LAYOUT\s+)?SLAB|ROOF\s+SLAB\s+(?:LAYOUT|PLAN|STEEL|FRAMING|DETAILS?)|"
        r"UPPER\s+ROOF\s+SLAB|SCHEDULE\s+OF\s+ROO?F\s+BEAMS?|ROOF\s+FRAMING\s+PLAN)\b",
    ):
        return {
            "detected_type": "roof_slab",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["roof_slab"]["extract_items"],
        }

    if _has_kw(
        up,
        r"\b(?:(?:2ND|SECOND)\s+(?:FLOOR\s+)?SLAB|(?:2ND|SECOND)\s+FLOOR\s+FRAMING|"
        r"SCHEDULE\s+OF\s+(?:2ND|SECOND)\s+SLAB)\b",
    ):
        return {
            "detected_type": "slab_2nd",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["slab_2nd"]["extract_items"],
        }

    if _has_kw(
        up,
        r"\b(?:(?:1ST|FIRST|F\.?)\s*FLOOR\s+SLAB|(?:1ST|FIRST)\s+SLAB|"
        r"G\.?\s*FLOOR\s+SLAB\s+LAYOUT|GROUND\s+FLOOR\s+COVERING\s+SLAB|"
        r"FIRST\s+FLOOR\s+FRAMING|SCHEDULE\s+OF\s+(?:FIRST|1ST)\s+SLAB|"
        r"SLAB\s*&\s*BEAM\s+PLAN)\b",
    ):
        return {
            "detected_type": "slab_1st",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["slab_1st"]["extract_items"],
        }

    # 5. Soft keyword fallback (low/medium confidence -> triggers AI Vision confirmation!)
    scores = {}
    for ptype, config in PAGE_ITEMS_MAP.items():
        if config.get("pdf_type") != "structural":
            continue
        score = 0
        for kw in config.get("drawing_keywords", []):
            if len(kw) <= 3:
                if re.search(rf"\b{re.escape(kw)}\b", up):
                    score += 1
            elif kw.upper() in up:
                score += 1
        scores[ptype] = score
    best = max(scores, key=scores.get) if scores else "unknown"
    best_score = scores.get(best, 0)
    if best_score > 0:
        return {
            "detected_type": best,
            "confidence": "medium" if best_score >= 2 else "low",
            "items": PAGE_ITEMS_MAP[best]["extract_items"],
        }
    return {"detected_type": "unknown", "confidence": "low", "items": []}


def _classify_architectural(raw_text: str, clean_text: str) -> dict:
    """High-precision deterministic classifier for UAE architectural PDF pages."""
    is_skip, reason = _is_non_takeoff_sheet(raw_text, clean_text, "architectural")
    if is_skip:
        return {"detected_type": "unknown", "confidence": "high", "items": [], "reason": reason}

    up = clean_text.upper()
    room_hits = len(_ROOM_WORDS_RE.findall(up))
    mark_hits = len(_PLAN_MARK_RE.findall(up))
    level_markers = _LEVEL_MARKER_RE.findall(up)

    # 1. Door & Window Schedules (explicit schedule title OR repeated DOOR-01 / WINDOW-01 blocks without room layout)
    has_sched_title = _has_kw(
        up,
        r"\b(?:DOOR\s*(?:&|AND|/)?\s*WINDOW\s+SCHEDULE|DOOR\s+SCHEDULE|WINDOW\s+SCHEDULE|"
        r"SCHEDULE\s+OF\s+(?:DOORS?|WINDOWS?|OPENINGS?)|DOORS?\s*(?:&|AND|/)\s*WINDOWS?\s+DETAILS?|"
        r"PANELS?\s*(?:&|AND)\s*DOORS?\s*(?:&|AND)\s*WINDOWS?|"
        r"DOORS?\s+DETAILS?|WINDOWS?\s+DETAILS?)\b",
    )
    has_glazing_spec = (
        room_hits < 3
        and _has_kw(up, r"\b(?:POWDER\s+COATED|UPVC\s+SECTIONS|ALUMINI?UM\s+SECTIONS)\b")
        and _has_kw(up, r"\b(?:WINDOW|DOOR)\b")
    )
    has_sched_items = (
        len(re.findall(r"\b(?:MAIN\s+DOOR|DOOR|WINDOW|PANEL)\s*[\-:]\s*0*\d+\b", up)) >= 3
        and room_hits < 3
    )
    if has_sched_title or has_sched_items or has_glazing_spec:
        return {
            "detected_type": "schedules",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["schedules"]["extract_items"],
        }

    # 2. Setting Out / Site Plan (plot limits, road, interlock, compound wall)
    has_site_title = _has_kw(
        up,
        r"\b(?:SETTING\s+OUT\s+PLAN|SITE\s+PLAN|PLOT\s+PLAN|MASTER\s+PLAN|LOCATION\s+PLAN|"
        r"SETTING\s+OUT\s+NOTES)\b",
    )
    has_site_content = (
        _has_kw(up, r"\b(?:INTERLOCKING\s+PAVEMENT|CAR\s+PARK|CAR\s+ENTRANCE|PLOT\s+LIMIT)\b")
        and room_hits < 3
    )
    if has_site_title or has_site_content:
        return {
            "detected_type": "setting_out",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["setting_out"]["extract_items"],
        }

    # 3. Explicit Floor Plan Titles (beats exterior elevation callout arrows on the same sheet!)
    if _has_kw(up, r"\b(?:GROUND\s+FLOOR\s+(?:ARCHITECTURAL\s+)?(?:PLAN|LAYOUT)|G\.?F\.?\s*(?:FLOOR\s+)?PLAN|PROPOSED\s+GROUND\s+FLOOR)\b") and not _has_kw(up, r"\bSTAIR\s+PLAN\b"):
        return {
            "detected_type": "ground_floor_plan",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["ground_floor_plan"]["extract_items"],
        }
    if _has_kw(up, r"\b(?:(?:1ST|FIRST)\s+FLOOR\s+(?:ARCHITECTURAL\s+)?(?:PLAN|LAYOUT)|1F\s+PLAN|F\.?F\.?\s+PLAN)\b") and not _has_kw(up, r"\bSTAIR\s+PLAN\b"):
        return {
            "detected_type": "first_floor_plan",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["first_floor_plan"]["extract_items"],
        }
    if _has_kw(up, r"\b(?:(?:2ND|SECOND)\s+FLOOR\s+(?:ARCHITECTURAL\s+)?(?:PLAN|LAYOUT)|2F\s+PLAN)\b"):
        return {
            "detected_type": "second_floor_plan",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["second_floor_plan"]["extract_items"],
        }
    if _has_kw(up, r"\b(?:ROOF\s+(?:FLOOR\s+)?(?:PLAN|LAYOUT)|TOP\s+ROOF\s+PLAN|UPPER\s+ROOF\s+PLAN)\b"):
        return {
            "detected_type": "roof_floor_plan",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["roof_floor_plan"]["extract_items"],
        }

    # 4. Elevations & Sections (distinguished cleanly from floor plans that only have callout arrows!)
    #    Real elevation/section sheets have multiple vertical level tags (F.F.L +0.60, +5.08, +9.56)
    #    OR explicit elevation/section headers WITHOUT floor-plan room/opening density.
    distinct_levels = {re.search(r"\d+\.\d{1,2}", m).group(0) for m in level_markers if re.search(r"\d+\.\d{1,2}", m)}
    has_elev_finishing = _has_kw(up, r"\b(?:ELEVATION\s+FINISHING|FRONT\s*&\s*(?:BACK|REAR)\s+ELEVATIONS?|LEFT\s*&\s*RIGHT\s+ELEVATIONS?|ELEVATIONS?\s*&\s*SECTIONS?|SECTION\s*[\-\s]*(?:A[\-\s]*A|B[\-\s]*B|1[\-\s]*1|2[\-\s]*2))\b")
    has_elev_words = _has_kw(up, r"\b(?:FRONT|REAR|BACK|LEFT|RIGHT|SIDE|NORTH|SOUTH|EAST|WEST)\s*(?:SIDE\s+)?ELEVATION\b|\bELEVATION\s+[A-D1-4]\b")

    if len(distinct_levels) >= 3 or (len(distinct_levels) >= 2 and room_hits < 4):
        return {
            "detected_type": "elevations",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["elevations"]["extract_items"],
        }
    if has_elev_finishing and mark_hits < 6:
        return {
            "detected_type": "elevations",
            "confidence": "high",
            "items": PAGE_ITEMS_MAP["elevations"]["extract_items"],
        }

    # 5. Floor plan with SHX stroke-font title (like Kayan Villa 10 P07/P08/P09!):
    #    Title text isn't selectable PDF text, ONLY room names + opening marks + elevation callouts are.
    #    Mark confidence='low' so the Vision refiner reads the actual SHX title block cleanly!
    if mark_hits >= 5 or room_hits >= 3:
        # Best deterministic guess in case Vision is unavailable (e.g., offline tests):
        if _has_kw(up, r"\b(?:MD[\-\s]?0*1|MAJLIS|KITCHEN|DINING|CAR\s+PARK|ENTRANCE)\b"):
            guess = "ground_floor_plan"
        elif _has_kw(up, r"\bDN\b") and not _has_kw(up, r"\bUP\b"):
            guess = "first_floor_plan"
        else:
            guess = "first_floor_plan"
        return {
            "detected_type": guess,
            "confidence": "low",
            "items": PAGE_ITEMS_MAP[guess]["extract_items"],
            "needs_vision": True,
        }

    # Roof plan with SHX title: single high F.F.L level repeated (e.g., F.F.L 9.56 × 5) + elevation callouts
    if len(distinct_levels) == 1 and len(level_markers) >= 3:
        try:
            lvl_val = float(next(iter(distinct_levels)))
            if lvl_val >= 6.0:
                return {
                    "detected_type": "roof_floor_plan",
                    "confidence": "low",
                    "items": PAGE_ITEMS_MAP["roof_floor_plan"]["extract_items"],
                    "needs_vision": True,
                }
        except ValueError:
            pass

    if has_elev_words and mark_hits < 4 and room_hits < 2:
        return {
            "detected_type": "elevations",
            "confidence": "low",
            "items": PAGE_ITEMS_MAP["elevations"]["extract_items"],
            "needs_vision": True,
        }

    return {"detected_type": "unknown", "confidence": "low", "items": [], "needs_vision": True}


def _classify_single(text: str, pdf_type: str) -> dict:
    """
    Deterministic first-pass page classifier (fast, word-boundary safe, domain-isolated).
    Returns {detected_type, confidence ('high'|'medium'|'low'), items, ...}.
    Pages with confidence != 'high' are refined visually by _ai_classify in Step 2.
    """
    clean = _clean_text(text)
    if pdf_type == "structural":
        return _classify_structural(text or "", clean)
    if pdf_type == "architectural":
        return _classify_architectural(text or "", clean)
    return {"detected_type": "unknown", "confidence": "low", "items": []}


def _detect_mime(img: bytes) -> str:
    return "image/jpeg" if img and img[:2] == b"\xff\xd8" else "image/png"


def _ai_classify(img_input, pdf_type: str, text_hint: str = ""):
    """Classify ONE page by vision when keyword matching is unsure (e.g. SHX stroke titles).
    Returns a PAGE_ITEMS_MAP key or 'unknown', or None on API failure."""
    from utils.key_manager import get_key_manager
    mgr = get_key_manager()
    if mgr.key_count() == 0:
        return None
    choices = _STRUCT_TYPES if pdf_type == "structural" else _ARCH_TYPES
    try:
        from google import genai
        from google.genai import types

        if isinstance(img_input, bytes):
            img = img_input
        elif isinstance(img_input, str) and os.path.exists(img_input):
            with open(img_input, "rb") as f:
                img = f.read()
        elif isinstance(img_input, np.ndarray):
            pil_img = page_to_pil(img_input)
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            img = buf.getvalue()
        else:
            return None

        mime_type = _detect_mime(img)
        if pdf_type == "architectural":
            guidance = (
                "Look at the drawing title block and layout. Pick ONE type from:\n"
                "- ground_floor_plan: Ground Floor architectural plan (rooms, entrance, majlis, kitchen)\n"
                "- first_floor_plan: First Floor architectural plan (upper bedrooms)\n"
                "- second_floor_plan: Second Floor architectural plan\n"
                "- roof_floor_plan: Roof / Top Roof / Penthouse plan\n"
                "- elevations: Villa Elevations or Sections (shows vertical building height & F.F.L levels)\n"
                "- setting_out: Site Plan / Setting Out Plan (shows full plot boundary, setbacks, interlock, compound wall)\n"
                "- schedules: Door and/or Window Schedule or Opening Details sheet\n"
                "- unknown: Cover sheet, general notes, regulations, legend, area calculation table, boundary wall elevation/details, stair details, 3D perspectives, or blank/non-takeoff sheet."
            )
        else:
            guidance = (
                "Look at the drawing title block and layout. Pick ONE type from:\n"
                "- foundations: Villa Footing / Foundation Layout Plan or Footing Schedule (NOT boundary wall)\n"
                "- tie_beam: Villa Tie Beam / Ground Beam / Plinth Beam Layout Plan or Tie Beam Schedule\n"
                "- column_layout: General Column Axis Layout Plan\n"
                "- upper_columns: Combined Column Schedule / Column Reinforcement Details table\n"
                "- neck_columns: Foundation-to-Tie-Beam / Ground / Neck Column Layout\n"
                "- columns_1f: Tie-Beam-to-First-Floor / First Floor Column Layout\n"
                "- columns_2f: First-to-Second-Floor / Second Floor Column Layout\n"
                "- columns_roof: First/Second-Floor-to-Roof / Roof Column Layout\n"
                "- slab_1st: First Floor Slab & Beam Framing Layout (or Ground Floor Covering Slab)\n"
                "- slab_2nd: Second Floor Slab & Beam Framing Layout\n"
                "- roof_slab: Roof Slab & Beam Framing Layout\n"
                "- unknown: Cover sheet, general notes, legend, typical rebar details, boundary/compound wall structural sheet, staircase details, or non-takeoff sheet."
            )

        prompt = (
            f"You are classifying a UAE residential villa {pdf_type} drawing sheet.\n"
            f"{guidance}\n"
            f"Allowed values: {choices}\n"
            'Reply ONLY with valid JSON: {"type": "<chosen_type>"}'
        )
        if text_hint:
            prompt += f"\nText excerpt on page: {text_hint[:400]}"

        for attempt in range(3):
            api_key, current_model = mgr.get_key_and_model()
            if not api_key or api_key == "NO_API_KEY_FOUND":
                return None

            try:
                client = genai.Client(api_key=api_key, http_options={"timeout": 25.0})
                resp = client.models.generate_content(
                    model=current_model,
                    contents=[types.Part.from_bytes(data=img, mime_type=mime_type), prompt],
                )
                raw = re.sub(r"```json|```", "", resp.text or "").strip()
                m_json = re.search(r"\{.*\}", raw, re.DOTALL)
                parsed = json.loads(m_json.group(0) if m_json else raw)
                result = str(parsed.get("type", "")).strip()
                if result == "unknown" or result in PAGE_ITEMS_MAP:
                    return result
                return None
            except Exception as e:
                err = str(e).lower()
                if "404" in err or "not found" in err or "no longer available" in err:
                    if hasattr(mgr, "mark_model_unavailable"):
                        mgr.mark_model_unavailable(current_model)
                    continue
                if any(code in err for code in ("429", "resource_exhausted", "quota", "503", "unavailable", "overloaded")):
                    mgr.mark_rate_limited(api_key, current_model)
                    time.sleep(0.4)
                    continue
                time.sleep(0.5)

        return None
    except Exception:
        return None


def classify_pages_hybrid(pages: list[dict], project_cache: str = "") -> list[dict]:
    """
    Refine any low/medium-confidence pages in `pages` concurrently using AI Vision
    (e.g. AutoCAD SHX stroke-font titles that cannot be read as PDF text).
    Each entry in `pages` has keys: pdf, page_index, text_full (optional), detected_type, confidence, ...
    """
    from utils.key_manager import get_key_manager
    mgr = get_key_manager()
    if mgr.key_count() == 0:
        return pages

    to_refine = []
    for idx, p in enumerate(pages):
        if p.get("confidence") == "high":
            continue
        prefix = "str" if p.get("pdf") == "structural" else "arch"
        pidx = p.get("page_index", 0)
        img_path = None
        if project_cache:
            for ext in ("jpg", "jpeg", "png"):
                cand = os.path.join(project_cache, f"{prefix}_page_{pidx}.{ext}")
                if os.path.exists(cand):
                    img_path = cand
                    break
        if img_path:
            to_refine.append((idx, img_path, p.get("pdf", "architectural"), p.get("text_preview", "")))

    if not to_refine:
        return pages

    workers = min(4, max(1, mgr.key_count()))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {
            ex.submit(_ai_classify, img_path, ptype, hint): idx
            for idx, img_path, ptype, hint in to_refine
        }
        for fut, idx in futs.items():
            try:
                ai_type = fut.result()
                if ai_type is not None:
                    pages[idx]["detected_type"] = ai_type
                    pages[idx]["auto_detected_type"] = ai_type
                    pages[idx]["confidence"] = "high" if ai_type != "unknown" else "medium"
                    pages[idx]["items"] = PAGE_ITEMS_MAP.get(ai_type, {}).get("extract_items", []) if ai_type != "unknown" else []
                    pages[idx]["method"] = "ai_vision"
            except Exception:
                pass
    return pages
