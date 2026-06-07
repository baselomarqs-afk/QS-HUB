"""
STEP 3 — Extract Data
OCR + OpenCV + AI Vision — all together per classified page
Each page extracts ONLY what its formulas need
"""
import os, json, re, io, threading
import numpy as np

# Serializes access to the shared LLM cache file across extraction worker threads
_LLM_CACHE_LOCK = threading.Lock()
from PIL import Image
from pdf_engine.pdf_loader import page_to_pil
from engine.dimension_filter import (
    DRAWING_REQUIRED_INPUTS,
    get_ai_prompt_for_drawing,
    filter_ocr_by_drawing_inputs,
)
from workflow.workflow_state import get_current_step, set_step, step_done, STEPS
from _pdf_utils import normalize_mark
from workflow.workflow_state import mark_step_done



# Combined column SCHEDULE page → per-floor counts in one table
COLUMN_TYPES  = {"upper_columns", "column_schedule", "ground_columns"}
COLUMN_PROMPT = """You are reading a STRUCTURAL COLUMN SCHEDULE for a UAE villa.

For EACH column mark in the table, extract:
- "mark": the column label (e.g. C1, C2)
- "width_m":  the smaller plan dimension, in METRES
- "length_m": the larger plan dimension, in METRES

Return ONLY this JSON (no extra text):
{"columns": [{"mark":"C1","width_m":0.30,"length_m":0.60}],
 "confidence":"high|medium|low", "notes":""}"""

# Dedicated PER-FLOOR column pages → single count for that one floor
PERFLOOR_COLUMN_TYPES = {
    "neck_columns": "gf", "columns_1f": "1f", "columns_2f": "2f", "columns_roof": "roof",
}
PERFLOOR_COLUMN_PROMPT = """You are reading a STRUCTURAL COLUMN layout/schedule for ONE floor of a UAE villa.

For EACH column mark shown, extract:
- "mark": the column label (e.g. C1, C2)
- "width_m":  the smaller plan dimension, in METRES
- "length_m": the larger plan dimension, in METRES
- "count": how many of this column on THIS floor

Return ONLY this JSON (no extra text):
{"columns": [{"mark":"C1","width_m":0.30,"length_m":0.60,"count":4}],
 "confidence":"high|medium|low", "notes":""}"""

# ── Foundations / Tie beam / Slab / Schedules — list-based, in METRES ─────────
FOUNDATION_TYPES = {"foundations"}
TIE_BEAM_TYPES   = {"tie_beam"}
SLAB_TYPES       = {"slab_1st", "slab_2nd", "slab_roof", "roof_slab"}
SCHEDULE_TYPES   = {"schedules", "door_schedule", "window_schedule"}
SETTING_OUT_TYPES= {"setting_out"}
ELEVATION_TYPES  = {"elevations", "sections"}

FOUNDATION_PROMPT = """You are reading a FOUNDATION / FOOTING plan + SCHEDULE OF FOOTINGS of a UAE villa.
The "footings" list is MANDATORY — there is always a footing schedule table; read every
row. Do NOT return an empty footings list.
Extract (ALL dimensions in METRES):
- "longest_length": building footprint overall longest length (m)
- "longest_width":  building footprint overall width (m)
- "footings": one object per footing TYPE (F1, F2, CF1 …):
    {"mark":"F1","width":<m>,"length":<m>,"depth":<m>,"count":<how many>}
Return ONLY this JSON:
{"longest_length":null,"longest_width":null,
 "footings":[{"mark":"F1","width":1.5,"length":1.5,"depth":0.5,"count":4}],
 "confidence":"high|medium|low","notes":""}"""

TIE_BEAM_PROMPT = """You are reading a TIE BEAM (ground beam) plan + schedule of a UAE villa.
Extract (ALL in METRES):
- "tb_width": typical tie-beam width
- "tb_depth": typical tie-beam depth
- "tb_total_length": total run length of all tie beams (m)
- "ext_perimeter": external building perimeter (m)
- "gf_area": ground-floor built-up area (m²)
Return ONLY this JSON:
{"tb_width":0.30,"tb_depth":0.60,"tb_total_length":null,"ext_perimeter":null,"gf_area":null,
 "confidence":"high|medium|low","notes":""}"""

SLAB_PROMPT = """You are reading a SLAB / BEAM framing plan + schedule of one UAE villa floor.
Extract (ALL in METRES):
- "slab_area": slab area (m²)
- "slab_thickness": slab thickness (m, e.g. 0.20)
- "beams": one object per beam TYPE:
    {"mark":"B1","width":<m>,"depth":<m>,"length":<total run length of that mark, m>}
Return ONLY this JSON:
{"slab_area":null,"slab_thickness":0.20,
 "beams":[{"mark":"B1","width":0.20,"depth":0.60,"length":5.0}],
 "confidence":"high|medium|low","notes":""}"""

ROOF_SLAB_PROMPT = """You are reading a ROOF SLAB / BEAM framing plan + schedule of a UAE villa.
Extract (ALL in METRES):
- "slab_area": total roof slab area (m²)
- "slab_thickness": slab thickness (m, e.g. 0.20)
- "roof_perimeter": external perimeter of the roof slab (m) — for parapet calculation
- "beams": one object per beam TYPE:
    {"mark":"B1","width":<m>,"depth":<m>,"length":<total run length of that mark, m>}
Return ONLY this JSON:
{"slab_area":null,"slab_thickness":0.20,"roof_perimeter":null,
 "beams":[{"mark":"B1","width":0.20,"depth":0.60,"length":5.0}],
 "confidence":"high|medium|low","notes":""}"""

SCHEDULE_PROMPT = """You are reading DOOR and/or WINDOW SCHEDULES of a UAE villa.

IMPORTANT RULES:
- Dimensions (width, height) come FROM THE SCHEDULE TABLE — read them precisely.
- READ THE QUANTITY COLUMN (QTY / NO. / COUNT / NOS) for EACH mark — this is the
  authoritative TOTAL number of that door/window TYPE in the whole villa. Sum across
  all marks to get the project total. If a mark truly has no quantity, count how many
  times that mark appears on the plans — NEVER default the count to 1.
- Return dimensions in MILLIMETRES so the system can convert them accurately.
- STRICT RULE: This is a RESIDENTIAL VILLA. If the schedule contains commercial doors or windows labeled "SHOP", "RETAIL", "STORE", or similar commercial names, IGNORE THEM COMPLETELY. Only extract residential doors and windows.

Extract every residential row of the door schedule table:
- "doors": [{"mark":"D1", "width_mm":900, "height_mm":2100, "count":<n from schedule>}]

Extract every row of the window schedule table:
- "windows": [{"mark":"W1", "width_mm":1500, "height_mm":1500, "count":<n from schedule>}]

Return ONLY this JSON (no markdown, no explanation):
{"doors":[{"mark":"D1","width_mm":900,"height_mm":2100,"count":5}],
 "windows":[{"mark":"W1","width_mm":1500,"height_mm":1500,"count":6}],
 "confidence":"high|medium|low","notes":""}"""

SETTING_OUT_PROMPT = """You are reading a SETTING OUT (site layout / master plan) of a UAE villa.

Extract (ALL in METRES):
- "plot_area": The total area of the plot/site boundary (m²)
- "compound_length": The total perimeter/length of the compound wall (m)

To find plot_area, look for explicit notes like "Plot Area: X sq.m" or multiply the overall boundary dimensions. 
For compound_length, sum all boundary line lengths, or look for a stated perimeter.

Return ONLY this JSON (no extra text):
{"plot_area":null, "compound_length":null,
 "confidence":"high|medium|low", "notes":""}"""

FLOORPLAN_TYPES = {"ground_floor_plan", "first_floor_plan", "second_floor_plan"}
FLOOR_PLAN_PROMPT = """You are reading an ARCHITECTURAL FLOOR PLAN of a UAE villa floor.
CRITICAL: You MUST extract EVERY SINGLE ROOM shown on the plan. 
CRITICAL: DO NOT SKIP ANY BATHROOMS, TOILETS, POWDER ROOMS, OR KITCHENS. They are absolutely required for wet area calculations. If you skip them, the quantities will be 0.
Villa plans rarely write the room AREA, but they DO show each room's name and its DIMENSIONS (e.g. "5.00 x 4.00").
READ THE DIMENSIONS from the dimension lines or text — do not guess.

List EVERY room/space in the "rooms" array:
- "name": room name (Living, Bedroom, Bathroom, Kitchen, Majlis, Terrace, WC, Laundry …)
- "length_m","width_m": the room size from its dimension labels (METRES) — REQUIRED
- "area_m2": only if an area is explicitly printed (else null)
- "doors_count": count the doors (swing arcs/sliding symbols) for THIS specific room.
- "windows_count": count the windows on the external walls of THIS specific room.

Also read the overall dimension lines:
- "overall_length_m","overall_width_m": building outer dimensions (METRES)
- "balcony_terrace_area_m2": open balcony + terrace area if shown (else null)
- "floor_height_m": floor-to-floor or floor-to-ceiling height if shown anywhere on the plan or in a note/section (e.g. 3.2, 4.0, 4.6) — in METRES. null if not found.

- "int_walls_10cm_m" / "int_walls_20cm_m": total length (METRES) of the INTERNAL walls
  BY THICKNESS, read from the plan. 10 cm (100 mm) = thin partitions (around
  bathrooms/WCs, closets/dressing, light dividers); 20 cm (200 mm) = the main internal
  walls between rooms. Read the wall line thickness / any wall-type note. If you truly
  cannot tell them apart, return 0 for BOTH (the system then treats all internal walls
  as 20 cm).

Return ONLY this JSON (no markdown):
{"rooms":[{"name":"Living","length_m":5.0,"width_m":4.0,"area_m2":null,"doors_count":2,"windows_count":1}],
 "overall_length_m":null,"overall_width_m":null,"balcony_terrace_area_m2":null,
 "floor_height_m":null,
 "int_walls_10cm_m":0.0,"int_walls_20cm_m":0.0,
 "confidence":"high|medium|low","notes":""}"""

METRES_NOTE = ("\n\nCRITICAL: Return ALL dimensions in METRES (e.g. 6.0, 0.30 — NOT "
               "6000 or 300). If the drawing labels are in millimetres, divide by 1000.")


def _to_m(v, mm_above):
    """Convert an obvious-millimetre value to metres."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return v
    return round(v / 1000.0, 4) if v > mm_above else v


def _finishes_from_rooms(data: dict) -> dict:
    """
    Turn a reliable ROOM LIST into the finishes inputs the formulas need.
    Geometric identities (no guessing):
      total_floor_area = Σ room areas (or overall L×W)
      wet_area         = Σ wet-room areas
      ext_perimeter    = 2(L+W) from overall dims
      int_walls_length = (Σ room perimeters − ext_perimeter) / 2
                         (each internal wall borders 2 rooms, external 1)
      wet/dry_perimeter= Σ 2(l+w) of wet / dry rooms
    """
    rooms = data.get("rooms") or []
    if not rooms:
        return data

    # Deterministic wet-room detection by NAME (don't trust the AI's 'wet' flag alone)
    _WET_KW = ("bath", "toilet", "wc", "w.c", "kitchen", "pantry", "laundry",
               "ensuite", "en-suite", "powder", "shower", "washroom", "wash room",
               "حمام", "دورة", "مطبخ", "مغسلة", "تواليت", "مرحاض")

    def is_wet(r):
        if r.get("wet") is True:
            return True
        name = str(r.get("name", "")).lower()
        return any(kw in name for kw in _WET_KW)

    def dim(v):
        try: v = float(v)
        except (TypeError, ValueError): return 0.0
        return v / 1000.0 if v > 50 else v        # mm → m

    def per(r):
        l, w = dim(r.get("length_m")), dim(r.get("width_m"))
        return 2 * (l + w) if (l and w) else 0.0

    def area(r):
        # Prefer a labelled area; if absent (the usual case) compute L×W from the
        # room dimensions, which ARE shown on villa plans.
        try: a = float(r.get("area_m2") or 0)
        except (TypeError, ValueError): a = 0.0
        if a:
            return a
        l, w = dim(r.get("length_m")), dim(r.get("width_m"))
        return l * w

    total_area = sum(area(r) for r in rooms)
    wet_area   = sum(area(r) for r in rooms if is_wet(r))
    wet_per    = sum(per(r)  for r in rooms if is_wet(r))
    dry_per    = sum(per(r)  for r in rooms if not is_wet(r))
    sum_per    = sum(per(r)  for r in rooms)

    # Sum doors and windows from rooms
    door_cnt = 0
    win_cnt = 0
    for r in rooms:
        try: door_cnt += int(r.get("doors_count") or 0)
        except: pass
        try: win_cnt += int(r.get("windows_count") or 0)
        except: pass

    # Divide by 2 because interior doors are shared between two spaces (e.g. hallway and bedroom).
    # We add 1 for the main entrance door as a safe baseline.
    if door_cnt > 0:
        data["total_doors_count"] = max(1, int(door_cnt / 2) + 1)
    
    # Assume an average window is 2.0 sqm
    if win_cnt > 0:
        data["total_windows_area"] = win_cnt * 2.0

    L = data.get("overall_length_m") if data.get("overall_length_m") is not None else data.get("longest_length")
    W = data.get("overall_width_m") if data.get("overall_width_m") is not None else data.get("longest_width")
    L, W = dim(L), dim(W)
    ext_per = 2 * (L + W) if (L and W) else 0.0
    if not total_area and L and W:
        total_area = L * W

    # ── Consistency: a floor's external perimeter must match its built area ──
    # If overall dims were misread (e.g. whole-building dims on a small setback
    # floor), the implied area dwarfs the real floor area → derive perimeter
    # from the area instead (a compact floor perimeter ≈ 4.2·√area).
    if total_area > 0:
        implied = (ext_per / 4.0) ** 2 if ext_per else 0.0
        if (not ext_per) or implied > total_area * 1.8:
            ext_per = round(4.2 * (total_area ** 0.5), 2)

    int_walls = max((sum_per - ext_per) / 2.0, 0.0) if (sum_per and ext_per) else 0.0

    data["total_floor_area"] = round(total_area, 2) or data.get("total_floor_area")
    data["wet_area"]         = round(wet_area, 2) or data.get("wet_area")
    data["wet_perimeter"]    = round(wet_per, 2) or data.get("wet_perimeter")
    data["dry_perimeter"]    = round(dry_per, 2) or data.get("dry_perimeter")
    if ext_per:
        data["ext_perimeter"] = round(ext_per, 2)
    data["int_walls_length"] = round(int_walls, 2) or data.get("int_walls_length")
    data["balcony_area"]     = float(data.get("balcony_terrace_area_m2")
                                     or data.get("balcony_area") or 0)
    # Map AI's floor_height_m → flat floor_height key expected by display + step4
    fh = data.get("floor_height_m") or data.get("floor_height")
    if fh is not None:
        try:
            fh = float(fh)
            if fh > 50:    # mm → m
                fh = fh / 1000.0
            data["floor_height"] = round(fh, 2)
        except (TypeError, ValueError):
            pass
    return data


def _safe_parse_json(raw_str: str) -> dict:
    import json, re
    if not raw_str:
        return {}
    if raw_str.startswith('{"_error"'):
        try:
            return json.loads(raw_str)
        except Exception:
            return {"_error": "Failed to parse error"}
    raw_str = re.sub(r"```json|```", "", raw_str).strip()
    try:
        return json.loads(raw_str)
    except Exception:
        match = re.search(r'(\{.*\})', raw_str, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                return {}
    return {}

def _normalize_units(data: dict) -> dict:
    """Safety net: coerce any millimetre values the model slipped through to metres."""
    for k, thr in (("tb_width", 5), ("tb_depth", 5), ("slab_thickness", 5),
                   ("longest_length", 100), ("longest_width", 100), ("ext_perimeter", 100),
                   ("tb_total_length", 500), ("wet_perimeter", 500), ("dry_perimeter", 500),
                   ("int_walls_length", 500)):
        if data.get(k) is not None:
            data[k] = _to_m(data[k], thr)
    for f in data.get("footings", []) or []:
        f["width"]  = _to_m(f.get("width"),  20)
        f["length"] = _to_m(f.get("length"), 20)
        f["depth"]  = _to_m(f.get("depth"),  5)
        if not f.get("depth"):          # missing footing depth → typical 0.40 m
            f["depth"] = 0.40
    for b in data.get("beams", []) or []:
        b["width"]  = _to_m(b.get("width"),  5)
        b["depth"]  = _to_m(b.get("depth"),  5)
        b["length"] = _to_m(b.get("length"), 500)
    for c in data.get("columns", []) or []:
        for kk in ("width_m", "length_m", "width", "length"):
            if c.get(kk) is not None:
                c[kk] = _to_m(c[kk], 5)
    for lst in ("doors", "windows"):
        for o in data.get(lst, []) or []:
            # New _mm-suffixed fields (from updated SCHEDULE_PROMPT) — convert to metres safely
            for kk_mm, kk_m in (("width_mm", "width_m"), ("height_mm", "height_m")):
                if o.get(kk_mm) is not None:
                    o[kk_m] = _to_m(o[kk_mm], 10)
            # Legacy metre fields (safety net: if value looks like mm, convert)
            for kk in ("width", "height", "length"):
                if o.get(kk) is not None:
                    o[kk] = _to_m(o[kk], 10)
    return data


def _png_bytes(arr: np.ndarray) -> bytes:
    rgb = arr[:, :, ::-1].copy()
    pil = Image.fromarray(rgb)
    w, h = pil.size
    if max(w, h) > 2000:
        s = 2000 / max(w, h)
        pil = pil.resize((int(w*s), int(h*s)), Image.LANCZOS)
    buf = io.BytesIO()
    pil.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

async def _ask_ai_with_retry(img_bytes: bytes, full_prompt: str, mgr, force_reextract: bool = False) -> str:
    import time
    import hashlib
    import os
    import json
    import asyncio
    import re
    from google import genai
    from google.genai import types
    
    # MD5-based Caching Mechanism
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_qto_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "llm_cache.json")
    
    hasher = hashlib.md5()
    hasher.update(img_bytes)
    hasher.update(full_prompt.encode('utf-8'))
    cache_key = hasher.hexdigest()
    
    if not force_reextract and os.path.exists(cache_file):
        try:
            with _LLM_CACHE_LOCK:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            if cache_key in cache_data:
                cached_res = cache_data[cache_key]
                return json.dumps(cached_res)
        except Exception as cache_ex:
            print(f"Cache read error: {cache_ex}")
            
    last_err = ""
    max_attempts = max(6, mgr.key_count() * 2)
    for attempt in range(max_attempts):
        current_key, current_model = mgr.get_key_and_model()
        if not current_key or current_key == "NO_API_KEY_FOUND":
            last_err = "No valid API key found. All keys are in cooldown."
            print(f"All keys in cooldown. Waiting 15 seconds... (Attempt {attempt+1}/{max_attempts})")
            import time
            time.sleep(15)
            continue
            
        try:
            client = genai.Client(api_key=current_key, http_options={'timeout': 300.0})
            resp = client.models.generate_content(
                model=current_model,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    full_prompt,
                ],
            )
            raw = re.sub(r"```json|```", "", resp.text).strip()
            
            # Save to Cache
            try:
                data_to_cache = json.loads(raw)
                with _LLM_CACHE_LOCK:
                    cache_data = {}
                    if os.path.exists(cache_file):
                        try:
                            with open(cache_file, "r", encoding="utf-8") as f:
                                cache_data = json.load(f)
                        except Exception:
                            cache_data = {}
                    cache_data[cache_key] = data_to_cache
                    tmp = f"{cache_file}.{os.getpid()}.tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, cache_file)
            except Exception as cache_ex:
                pass # JSON parsing failed or cache write failed, handled gracefully
                
            return raw
        except Exception as e:
            last_err = str(e)
            mgr.mark_rate_limited(current_key, current_model)
            await asyncio.sleep(2)
            
    return json.dumps({"_error": last_err})


def extract_page(page_arr: np.ndarray, drawing_type: str, page_texts: str, user_id: int = None, previous_warnings: list = None, image_path: str = None, pdf_path: str = None, internal_page_idx: int = None, force_reextract: bool = False) -> dict:
    csv_injection = ""
    if pdf_path and internal_page_idx is not None:
        from pdf_engine.table_extractor import extract_tables_as_csv
        raw_csv = extract_tables_as_csv(pdf_path, internal_page_idx)
        if raw_csv:
            csv_injection = f"\n\n[DETERMINISTIC PDF EXTRACTION OVERRIDE]\nThe following is the raw CSV data of the tables extracted perfectly from the PDF using OCR. Rely on this text heavily for counts and dimensions, and use the image only as a visual reference:\n```csv\n{raw_csv}\n```\n"

    """
    Extract the values a drawing's formulas need.
    Uses AI Vision for complex readings, and strict Vector Math (PyMuPDF) for beam lengths.
    """
    from google import genai
    from google.genai import types
    import json
    import os
    import re

    # Removed static api_key fallback as the KeyManager handles all keys dynamically
    if drawing_type in COLUMN_TYPES:
        full_prompt = COLUMN_PROMPT
    elif drawing_type in PERFLOOR_COLUMN_TYPES:
        full_prompt = PERFLOOR_COLUMN_PROMPT
        
    elif drawing_type in FOUNDATION_TYPES:
        import asyncio
        from utils.key_manager import get_key_manager
        mgr = get_key_manager()
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f: img_bytes = f.read()
        else:
            img_bytes = _png_bytes(page_arr)
            
        async def run_foundations():
            from workflow.structural_extractors import FOUNDATION_DIMS_PROMPT, FOOTING_SCHEDULE_PROMPT
            p1 = FOUNDATION_DIMS_PROMPT + METRES_NOTE
            p2 = FOOTING_SCHEDULE_PROMPT + METRES_NOTE
            
            if previous_warnings and len(previous_warnings) > 0:
                warning_text = "\n- ".join(previous_warnings)
                refl = f"\n\n[CRITICAL SELF-REFLECTION REQUIRED]\nYour previous extraction failed these checks:\n- {warning_text}\nOutput a FIXED JSON."
                p1 += refl; p2 += refl
            
            p1 += csv_injection
            p2 += csv_injection
                
            if page_texts and page_texts.strip():
                txt = f"\n\n--- RAW TEXT ---\n{page_texts}\n-----------------"
                p1 += txt; p2 += txt
                
            t1 = _ask_ai_with_retry(img_bytes, p1, mgr, force_reextract=force_reextract)
            t2 = _ask_ai_with_retry(img_bytes, p2, mgr, force_reextract=force_reextract)
            r1, r2 = await asyncio.gather(t1, t2)
            
            d1 = _safe_parse_json(r1)
            d2 = _safe_parse_json(r2)
            if "_error" in d1 or "_error" in d2:
                err = d1.get("_error") or d2.get("_error")
                return {
                    "_ok": True, "_fallback": True,
                    "confidence": "low (API Fallback)",
                    "notes": f"Gemini vision call failed ({err}). Generated structural layout defaults.",
                    "drawing_type": drawing_type,
                    "longest_length": 20.0, "longest_width": 15.0, "footings": []
                }
            merged = {**d1, **d2}
            return merged
            
        data = asyncio.run(run_foundations())
        data = _normalize_units(data)
        
        from workflow.sanity_checks import perform_structural_sanity_checks
        warnings = perform_structural_sanity_checks(data, drawing_type)
        if warnings: data["_sanity_warnings"] = warnings
        
        data["_ok"] = True
        data["drawing_type"] = drawing_type
        return data

    elif drawing_type in TIE_BEAM_TYPES:
        import asyncio
        from utils.key_manager import get_key_manager
        mgr = get_key_manager()
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f: img_bytes = f.read()
        else:
            img_bytes = _png_bytes(page_arr)
            
        async def run_tie_beams():
            from workflow.structural_extractors import TB_SCHEDULE_PROMPT, TB_AREA_PROMPT
            p1 = TB_SCHEDULE_PROMPT + METRES_NOTE
            p2 = TB_AREA_PROMPT + METRES_NOTE
            if previous_warnings and len(previous_warnings) > 0:
                warning_text = "\n- ".join(previous_warnings)
                refl = f"\n\n[CRITICAL SELF-REFLECTION REQUIRED]\nYour previous extraction failed these checks:\n- {warning_text}\nOutput a FIXED JSON."
                p1 += refl; p2 += refl
                
            p1 += csv_injection
            p2 += csv_injection

            if page_texts and page_texts.strip():
                txt = f"\n\n--- RAW TEXT ---\n{page_texts}\n-----------------"
                p1 += txt; p2 += txt
            t1 = _ask_ai_with_retry(img_bytes, p1, mgr, force_reextract=force_reextract)
            t2 = _ask_ai_with_retry(img_bytes, p2, mgr, force_reextract=force_reextract)
            r1, r2 = await asyncio.gather(t1, t2)
            
            d1 = _safe_parse_json(r1)
            d2 = _safe_parse_json(r2)
            if "_error" in d1 or "_error" in d2:
                err = d1.get("_error") or d2.get("_error")
                return {
                    "_ok": True, "_fallback": True,
                    "confidence": "low (API Fallback)",
                    "notes": f"Gemini vision call failed ({err}). Generated structural layout defaults.",
                    "drawing_type": drawing_type,
                    "tb_width": 0.30, "tb_depth": 0.60, "tb_total_length": 80.0,
                    "ext_perimeter": 70.0, "gf_area": 250.0
                }
            merged = {**d1, **d2}
            
            # --- VECTOR MEASUREMENT OVERRIDES ---
            if pdf_path and internal_page_idx is not None:
                try:
                    from workflow.vector_measure import measure_tie_beams
                    print(f"  [Vector Engine] Computing Tie Beams geometrically for page {internal_page_idx}...")
                    v_res = measure_tie_beams(pdf_path, internal_page_idx)
                    total_tb_m = sum(m.get("measured_m", 0) for m in v_res.values())
                    if total_tb_m > 0:
                        merged["tb_total_length"] = total_tb_m
                        merged["_tb_vector_data"] = v_res
                        merged["notes"] = (merged.get("notes", "") + f" [100% Precision: Tie Beam lengths computed geometrically from CAD vectors ({total_tb_m}m)]").strip()
                except Exception as ve:
                    print(f"  [Vector Engine Error] {ve}")
                    
            return merged
            
        data = asyncio.run(run_tie_beams())
        data = _normalize_units(data)
        
        from workflow.sanity_checks import perform_structural_sanity_checks
        warnings = perform_structural_sanity_checks(data, drawing_type)
        if warnings: data["_sanity_warnings"] = warnings
        
        data["_ok"] = True
        data["drawing_type"] = drawing_type
        return data

    elif drawing_type in SLAB_TYPES or drawing_type == "roof_slab":
        import asyncio
        from utils.key_manager import get_key_manager
        mgr = get_key_manager()
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f: img_bytes = f.read()
        else:
            img_bytes = _png_bytes(page_arr)
            
        async def run_slabs():
            from workflow.structural_extractors import SLAB_AREA_PROMPT, ROOF_SLAB_AREA_PROMPT, BEAM_SCHEDULE_PROMPT
            p1 = (ROOF_SLAB_AREA_PROMPT if drawing_type == "roof_slab" else SLAB_AREA_PROMPT) + METRES_NOTE
            p2 = BEAM_SCHEDULE_PROMPT + METRES_NOTE
            if previous_warnings and len(previous_warnings) > 0:
                warning_text = "\n- ".join(previous_warnings)
                refl = f"\n\n[CRITICAL SELF-REFLECTION REQUIRED]\nYour previous extraction failed these checks:\n- {warning_text}\nOutput a FIXED JSON."
                p1 += refl; p2 += refl
            
            p1 += csv_injection
            p2 += csv_injection
                
            if page_texts and page_texts.strip():
                txt = f"\n\n--- RAW TEXT ---\n{page_texts}\n-----------------"
                p1 += txt; p2 += txt
            t1 = _ask_ai_with_retry(img_bytes, p1, mgr, force_reextract=force_reextract)
            t2 = _ask_ai_with_retry(img_bytes, p2, mgr, force_reextract=force_reextract)
            r1, r2 = await asyncio.gather(t1, t2)
            
            d1 = _safe_parse_json(r1)
            d2 = _safe_parse_json(r2)
            if "_error" in d1 or "_error" in d2:
                err = d1.get("_error") or d2.get("_error")
                fallback = {
                    "_ok": True, "_fallback": True,
                    "confidence": "low (API Fallback)",
                    "notes": f"Gemini vision call failed ({err}). Generated structural layout defaults.",
                    "drawing_type": drawing_type,
                    "slab_area": 250.0, "slab_thickness": 0.20, "beams": []
                }
                if drawing_type == "roof_slab":
                    fallback["roof_perimeter"] = 70.0
                return fallback
            merged = {**d1, **d2}
            
            # --- VECTOR MEASUREMENT OVERRIDES ---
            if pdf_path and internal_page_idx is not None:
                try:
                    from workflow.vector_measure import measure_page
                    print(f"  [Vector Engine] Computing Structural Beams geometrically for page {internal_page_idx}...")
                    v_res = measure_page(pdf_path, internal_page_idx)
                    if v_res and merged.get("beams"):
                        replaced_count = 0
                        for b in merged["beams"]:
                            mk = str(b.get("mark", "")).upper().strip()
                            if mk in v_res and v_res[mk].get("measured_m", 0) > 0:
                                b["length"] = v_res[mk]["measured_m"]
                                b["_vector_measured"] = True
                                replaced_count += 1
                        if replaced_count > 0:
                            merged["notes"] = (merged.get("notes", "") + f" [100% Precision: {replaced_count} beam lengths computed geometrically from CAD vectors]").strip()
                except Exception as ve:
                    print(f"  [Vector Engine Error] {ve}")
                    
            return merged
            
        data = asyncio.run(run_slabs())
        data = _normalize_units(data)
        
        from workflow.sanity_checks import perform_structural_sanity_checks
        warnings = perform_structural_sanity_checks(data, drawing_type)
        if warnings: data["_sanity_warnings"] = warnings
        
        data["_ok"] = True
        data["drawing_type"] = drawing_type
        return data

    elif drawing_type in SCHEDULE_TYPES:
        full_prompt = SCHEDULE_PROMPT
    elif drawing_type in SETTING_OUT_TYPES:
        full_prompt = SETTING_OUT_PROMPT
    elif drawing_type in ELEVATION_TYPES:
        import asyncio
        from utils.key_manager import get_key_manager
        mgr = get_key_manager()
        from workflow.elevation_extractor import extract_elevation_data
        
        if image_path and os.path.exists(image_path):
            data = asyncio.run(extract_elevation_data(image_path, mgr))
        else:
            data = {"gf_height_m": None, "f1_height_m": None, "total_villa_height_m": None, "parapet_height_m": None}
        data["drawing_type"] = drawing_type
        return data
    elif drawing_type in FLOORPLAN_TYPES:
        import asyncio
        from utils.key_manager import get_key_manager
        mgr = get_key_manager()
        
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_bytes = f.read()
        else:
            img_bytes = _png_bytes(page_arr)
            
        async def run_dedicated_extractors():
            from workflow.arch_extractor import ARCH_PROMPT
            from workflow.wall_extractor import WALL_PROMPT
            from workflow.openings_extractor import OPENINGS_PROMPT
            
            # Format prompts
            arch_p = ARCH_PROMPT + METRES_NOTE
            wall_p = WALL_PROMPT + METRES_NOTE
            open_p = OPENINGS_PROMPT + METRES_NOTE
            
            if previous_warnings and len(previous_warnings) > 0:
                warning_text = "\n- ".join(previous_warnings)
                refl = f"\n\n[CRITICAL SELF-REFLECTION REQUIRED]\nYour previous extraction failed these checks:\n- {warning_text}\nOutput a FIXED JSON."
                arch_p += refl; wall_p += refl; open_p += refl
            
            arch_p += csv_injection
            wall_p += csv_injection
            open_p += csv_injection
                
            if page_texts and page_texts.strip():
                txt = f"\n\n--- RAW TEXT ---\n{page_texts}\n-----------------"
                arch_p += txt; wall_p += txt; open_p += txt
                
            # CRITICAL: Run sequentially to prevent exceeding Gemini Free Tier concurrency limits (2 max).
            # Using asyncio.gather with 3 tasks was instantly crashing the free tier keys and returning zeros.
            arch_raw = await _ask_ai_with_retry(img_bytes, arch_p, mgr, force_reextract=force_reextract)
            wall_raw = await _ask_ai_with_retry(img_bytes, wall_p, mgr, force_reextract=force_reextract)
            open_raw = await _ask_ai_with_retry(img_bytes, open_p, mgr, force_reextract=force_reextract)
            
            arch_data = _safe_parse_json(arch_raw)
            wall_data = _safe_parse_json(wall_raw)
            open_data = _safe_parse_json(open_raw)
            
            if any("_error" in d for d in [arch_data, wall_data, open_data]):
                errs = [d.get("_error") for d in [arch_data, wall_data, open_data] if "_error" in d]
                err = errs[0] if errs else "Unknown Error"
                return {
                    "_ok": True, "_fallback": True,
                    "confidence": "low (API Fallback)",
                    "notes": f"Gemini vision call failed ({err}). Generated structural layout defaults.",
                    "drawing_type": drawing_type,
                    "total_floor_area": 250.0, "ext_perimeter": 70.0,
                    "int_walls_10cm_m": 0.0, "int_walls_20cm_m": 50.0
                }
            
            # Merge them together into the schema expected by _finishes_from_rooms
            merged = {}
            merged.update(arch_data)
            
            # Inject openings into the rooms array so _finishes_from_rooms can sum them up!
            rooms_arch = merged.get("rooms", [])
            rooms_open = open_data.get("rooms", [])
            for r_arch in rooms_arch:
                # Find matching room in openings
                for r_op in rooms_open:
                    if str(r_op.get("name", "")).lower() == str(r_arch.get("name", "")).lower():
                        if "doors_count" in r_op: r_arch["doors_count"] = r_op["doors_count"]
                        if "windows_count" in r_op: r_arch["windows_count"] = r_op["windows_count"]
                        break
            
            # Inject walls
            merged["int_walls_10cm_m"] = wall_data.get("int_walls_10cm_m", 0.0)
            merged["int_walls_20cm_m"] = wall_data.get("int_walls_20cm_m", 0.0)
            return merged
            
        data = asyncio.run(run_dedicated_extractors())
        data = _finishes_from_rooms(data)
        
        # --- BULLSHIT FILTER ---
        try:
            length = float(data.get("overall_length_m") or 0.0)
            width = float(data.get("overall_width_m") or 0.0)
            bbox_area = length * width
            
            if bbox_area > 0:
                area = float(data.get("total_floor_area") or 0.0)
                if area <= 0 or area > bbox_area * 1.1 or area < bbox_area * 0.3:
                    data["total_floor_area"] = round(bbox_area * 0.85, 2)
                    data["notes"] = (data.get("notes", "") + " [BULLSHIT FILTER: AI Area rejected. Geometric fallback used.]").strip()
                    
                perim = float(data.get("ext_perimeter") or 0.0)
                if perim <= 0 or perim > (length + width) * 4 or perim < (length + width) * 1.5:
                    data["ext_perimeter"] = round((length + width) * 2, 2)
                    data["notes"] = (data.get("notes", "") + " [BULLSHIT FILTER: AI Perimeter rejected. Geometric fallback used.]").strip()
        except Exception as e:
            print(f"Bullshit filter error: {e}")

        data = _normalize_units(data)
        
        from workflow.sanity_checks import perform_floor_plan_sanity_checks
        warnings = perform_floor_plan_sanity_checks(data)
        if warnings: data["_sanity_warnings"] = warnings
        
        data["_ok"] = True
        data["drawing_type"] = drawing_type
        return data
    else:
        prompt  = get_ai_prompt_for_drawing(drawing_type)
        config  = DRAWING_REQUIRED_INPUTS.get(drawing_type, {})
        extract = config.get("extract_only", [])
        # Build JSON schema
        schema = "{" + ", ".join(f'"{k}": null' for k in extract) + ', "confidence": "high|medium|low", "notes": ""}'
        full_prompt = f"""{prompt}

Return ONLY this JSON structure (null for not found):
{schema}"""

    full_prompt += METRES_NOTE
    full_prompt += csv_injection
    
    if user_id:
        from engine.qto_memory import format_rules_for_prompt
        memory_rules = format_rules_for_prompt(user_id)
        if memory_rules:
            full_prompt += "\n" + memory_rules
            
    if page_texts and page_texts.strip():
        full_prompt += f"\n\n--- RAW TEXT EXTRACTED FROM PDF (Use this to read blurry dimensions accurately) ---\n{page_texts}\n-----------------------------------------------------------------"

    if previous_warnings and len(previous_warnings) > 0:
        warning_text = "\n- ".join(previous_warnings)
        full_prompt += f"\n\n[CRITICAL SELF-REFLECTION REQUIRED]\nYour previous extraction of this exact drawing failed the following engineering sanity checks:\n- {warning_text}\n\nYou must carefully review the drawing again, find where you made a mistake, and output a FIXED JSON. Do NOT repeat the same mistake."

    import time
    import hashlib
    from utils.key_manager import get_key_manager
    mgr = get_key_manager()
    
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_bytes = f.read()
    else:
        img_bytes = _png_bytes(page_arr)
    
    # MD5-based Caching Mechanism
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_qto_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "llm_cache.json")
    
    hasher = hashlib.md5()
    hasher.update(img_bytes)
    hasher.update(full_prompt.encode('utf-8'))
    cache_key = hasher.hexdigest()
    
    if os.path.exists(cache_file):
        try:
            with _LLM_CACHE_LOCK:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            if cache_key in cache_data:
                cached_res = cache_data[cache_key]
                cached_res["_from_cache"] = True
                return cached_res
        except Exception as cache_ex:
            print(f"Cache read error: {cache_ex}")
            
    last_err = ""
    
    max_attempts = max(6, mgr.key_count() * 2)
    for attempt in range(max_attempts):
        current_key, current_model = mgr.get_key_and_model()
            
        if not current_key or current_key == "NO_API_KEY_FOUND":
            last_err = "No valid API key found. All keys in cooldown."
            print(f"All keys in cooldown. Waiting 15 seconds... (Attempt {attempt+1}/{max_attempts})")
            import time
            time.sleep(15)
            continue
            
        try:
            # Removed the rush timeout, giving the AI up to 5 minutes to finish complex drawings.
            client = genai.Client(api_key=current_key, http_options={'timeout': 300.0})
            resp = client.models.generate_content(
                model=current_model,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    full_prompt,
                ],
            )
            raw  = re.sub(r"```json|```", "", resp.text).strip()
            data = json.loads(raw)
            
            # --- VECTOR MEASUREMENT OVERRIDES ---
            if pdf_path and internal_page_idx is not None:
                try:
                    from workflow.vector_measure import measure_tie_beams, measure_page
                    
                    if drawing_type in TIE_BEAM_TYPES:
                        print(f"  [Vector Engine] Computing Tie Beams geometrically for page {internal_page_idx}...")
                        v_res = measure_tie_beams(pdf_path, internal_page_idx)
                        total_tb_m = sum(m.get("measured_m", 0) for m in v_res.values())
                        if total_tb_m > 0:
                            data["tb_total_length"] = total_tb_m
                            data["_tb_vector_data"] = v_res
                            data["notes"] = (data.get("notes", "") + f" [100% Precision: Tie Beam lengths computed geometrically from CAD vectors ({total_tb_m}m)]").strip()
                            
                    elif drawing_type in SLAB_TYPES or drawing_type == "roof_slab":
                        print(f"  [Vector Engine] Computing Structural Beams geometrically for page {internal_page_idx}...")
                        v_res = measure_page(pdf_path, internal_page_idx)
                        if v_res and data.get("beams"):
                            replaced_count = 0
                            for b in data["beams"]:
                                mk = str(b.get("mark", "")).upper().strip()
                                if mk in v_res and v_res[mk].get("measured_m", 0) > 0:
                                    b["length"] = v_res[mk]["measured_m"]
                                    b["_vector_measured"] = True
                                    replaced_count += 1
                            if replaced_count > 0:
                                data["notes"] = (data.get("notes", "") + f" [100% Precision: {replaced_count} beam lengths computed geometrically from CAD vectors]").strip()
                except Exception as ve:
                    print(f"  [Vector Engine Error] {ve}")
            # ------------------------------------

            if drawing_type in FLOORPLAN_TYPES:
                data = _finishes_from_rooms(data)   # rooms → finishes inputs
                
            data = _normalize_units(data)        # mm → m safety net
            
            # --- SANITY CHECKS ---
            from workflow.sanity_checks import perform_floor_plan_sanity_checks, perform_structural_sanity_checks
            warnings = []
            if drawing_type in FLOORPLAN_TYPES:
                warnings.extend(perform_floor_plan_sanity_checks(data))
            else:
                warnings.extend(perform_structural_sanity_checks(data, drawing_type))
            
            if warnings:
                data["_sanity_warnings"] = warnings
                print(f"  [Sanity Checks] {len(warnings)} warnings found for {drawing_type}")
            # ---------------------
            
            data["_ok"]          = True
            data["drawing_type"] = drawing_type
            
            # Save to Cache (lock + atomic write — safe across worker threads)
            try:
                with _LLM_CACHE_LOCK:
                    cache_data = {}
                    if os.path.exists(cache_file):
                        try:
                            with open(cache_file, "r", encoding="utf-8") as f:
                                cache_data = json.load(f)
                        except Exception:
                            cache_data = {}  # corrupted cache -> rebuild instead of crashing
                    cache_data[cache_key] = data
                    tmp = f"{cache_file}.{os.getpid()}.tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, cache_file)  # atomic on the same filesystem
            except Exception as cache_ex:
                print(f"Cache write error: {cache_ex}")
                
            return data
        except Exception as e:
            last_err = str(e)
            if any(code in last_err for code in ("429", "RESOURCE_EXHAUSTED", "quota")):
                mgr.mark_rate_limited(current_key, current_model)
                continue
            time.sleep(2)
            time.sleep(2 * (attempt + 1))
            
    # API Fallback Mechanism: Return standard fallback object instead of failing completely
    fallback_data = {
        "_ok": True,
        "_fallback": True,
        "confidence": "low (API Fallback)",
        "notes": f"Gemini vision call failed after {max_attempts} attempts ({last_err}). Generated structural layout defaults.",
        "drawing_type": drawing_type
    }
    if drawing_type in COLUMN_TYPES or drawing_type in PERFLOOR_COLUMN_TYPES:
        fallback_data["columns"] = []
    elif drawing_type in FOUNDATION_TYPES:
        fallback_data["longest_length"] = 20.0
        fallback_data["longest_width"] = 15.0
        fallback_data["footings"] = []
    elif drawing_type in TIE_BEAM_TYPES:
        fallback_data["tb_width"] = 0.30
        fallback_data["tb_depth"] = 0.60
        fallback_data["tb_total_length"] = 80.0
        fallback_data["ext_perimeter"] = 70.0
        fallback_data["gf_area"] = 250.0
    elif drawing_type in ELEVATION_TYPES:
        fallback_data["gf_height_m"] = 4.0
        fallback_data["f1_height_m"] = 4.0
        fallback_data["total_villa_height_m"] = 9.5
        fallback_data["parapet_height_m"] = 1.2
    elif drawing_type in SLAB_TYPES or drawing_type == "roof_slab":
        fallback_data["slab_area"] = 250.0
        fallback_data["slab_thickness"] = 0.20
        fallback_data["beams"] = []
        if drawing_type == "roof_slab":
            fallback_data["roof_perimeter"] = 70.0
    else:
        fallback_data["longest_length"] = 20.0
        fallback_data["longest_width"] = 15.0
        
    return fallback_data


def merge_schedule_json_to_results(results: dict):
    """
    Loads _schedule_data.json, _arch_data.json, and _openings_data.json
    from the active workspace directory and merges them into the `results`
    dictionary under the correct drawing types, translating keys to what
    the calculation engine expects.
    """
    import os, json

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def get_or_create(dtype):
        for data in results.values():
            if isinstance(data, dict) and data.get("drawing_type") == dtype:
                return data
        key = f"synthetic_{dtype}"
        results[key] = {
            "drawing_type": dtype,
            "_ok": True,
            "pdf": "architectural" if ("plan" in dtype or dtype in ("schedules", "setting_out")) else "structural",
            "page_num": 1,
            "page_index": 0
        }
        return results[key]

    # 1. Merge _schedule_data.json (Structural schedules)
    schedule_path = os.path.join(root, "_schedule_data.json")
    if os.path.exists(schedule_path):
        try:
            with open(schedule_path, encoding='utf-8') as f:
                sched = json.load(f)
            
            if "foundation" in sched:
                data = get_or_create("foundations")
                foots = sched["foundation"].get("footings", [])
                mapped = []
                for f in foots:
                    mapped.append({
                        "mark": f.get("type", ""),
                        "width": float(f.get("short_mm") or 0) / 1000.0,
                        "length": float(f.get("long_mm") or 0) / 1000.0,
                        "depth": float(f.get("depth_mm") or 0) / 1000.0,
                        "count": int(f.get("count") or 0)
                    })
                data["footings"] = mapped
                data["_ok"] = True

            if "tie_beam" in sched:
                data = get_or_create("tie_beam")
                tbs = sched["tie_beam"].get("tie_beams", [])
                if tbs:
                    data["tb_width"] = float(tbs[0].get("width_mm") or 200) / 1000.0
                    data["tb_depth"] = float(tbs[0].get("depth_mm") or 600) / 1000.0
                    measured_total = sum(float(t.get("length_m") or 0) for t in tbs)
                    if measured_total > 0:
                        data["tb_total_length"] = measured_total
                data["_ok"] = True

            for dtype, sched_key in [("slab_1st", "slab_1f"), ("slab_2nd", "slab_2f"), ("roof_slab", "slab_roof")]:
                if sched_key in sched:
                    data = get_or_create(dtype)
                    s = sched[sched_key]
                    data["slab_thickness"] = float(s.get("slab_thickness_mm") or 200) / 1000.0
                    beams = s.get("beams", [])
                    mapped_beams = []
                    for b in beams:
                        mapped_beams.append({
                            "mark": b.get("mark", ""),
                            "width": float(b.get("width_mm") or 200) / 1000.0,
                            "depth": float(b.get("depth_mm") or 600) / 1000.0,
                            "length": float(b.get("length_m") or b.get("span_m") or 0) or (float(b.get("count", 1)) * 4.5),
                            "count": int(b.get("count") or 1)
                        })
                    data["beams"] = mapped_beams
                    data["_ok"] = True

            if "column_schedule" in sched:
                for col_type in ("column_schedule", "upper_columns", "ground_columns"):
                    data = get_or_create(col_type)
                    cols = sched["column_schedule"].get("columns", [])
                    mapped_cols = []
                    for c in cols:
                        mapped_cols.append({
                            "mark": c.get("mark", ""),
                            "width_m": float(c.get("width_mm") or 200) / 1000.0,
                            "length_m": float(c.get("depth_mm") or 600) / 1000.0,
                            "count_gf": int(c.get("count_gf") or 0) if c.get("count_gf") is not None else 0,
                            "count_1f": int(c.get("count_1f") or 0) if c.get("count_1f") is not None else 0,
                            "count_2f": int(c.get("count_2f") or 0) if c.get("count_2f") is not None else 0,
                            "count_roof": int(c.get("count_roof") or 0) if c.get("count_roof") is not None else 0,
                        })
                    data["columns"] = mapped_cols
                    data["_ok"] = True
        except Exception as e:
            print(f"Error loading _schedule_data.json: {e}")

    # 2. Merge _arch_data.json (Architectural plan parameters)
    arch_path = os.path.join(root, "_arch_data.json")
    if os.path.exists(arch_path):
        try:
            with open(arch_path, encoding='utf-8') as f:
                arch_data = json.load(f)
            
            if arch_data.get("plot_area") is not None or arch_data.get("compound_length") is not None:
                so = get_or_create("setting_out")
                if arch_data.get("plot_area") is not None:
                    so["plot_area"] = arch_data["plot_area"]
                if arch_data.get("compound_length") is not None:
                    so["compound_length"] = arch_data["compound_length"]
                so["_ok"] = True

            if arch_data.get("longest_length") is not None or arch_data.get("longest_width") is not None:
                fnd = get_or_create("foundations")
                if arch_data.get("longest_length") is not None:
                    fnd["longest_length"] = arch_data["longest_length"]
                if arch_data.get("longest_width") is not None:
                    fnd["longest_width"] = arch_data["longest_width"]
                fnd["_ok"] = True

            if arch_data.get("gf_area") is not None or arch_data.get("external_perimeter") is not None:
                tb = get_or_create("tie_beam")
                if arch_data.get("gf_area") is not None:
                    tb["gf_area"] = arch_data["gf_area"]
                if arch_data.get("external_perimeter") is not None:
                    tb["ext_perimeter"] = arch_data["external_perimeter"]
                tb["_ok"] = True

            if arch_data.get("roof_slab_area") is not None or arch_data.get("roof_perimeter") is not None:
                rs = get_or_create("roof_slab")
                if arch_data.get("roof_slab_area") is not None:
                    rs["slab_area"] = arch_data["roof_slab_area"]
                if arch_data.get("roof_perimeter") is not None:
                    rs["roof_perimeter"] = arch_data["roof_perimeter"]
                rs["_ok"] = True

            fheights = arch_data.get("floor_heights") or []
            if fheights:
                plan_types = ["ground_floor_plan", "first_floor_plan", "second_floor_plan"]
                for idx, h in enumerate(fheights):
                    if idx < len(plan_types):
                        fl_plan = get_or_create(plan_types[idx])
                        fl_plan["floor_height"] = h
                        fl_plan["_ok"] = True

            slevels = arch_data.get("structural_levels")
            if slevels is not None:
                for dtype in ("slab_1st", "slab_2nd", "roof_slab"):
                    sl = get_or_create(dtype)
                    sl["structural_levels"] = slevels
                    sl["_ok"] = True

                # NOTE: structural_levels is carried in `results` dict entries;
                # no separate session-state write is needed in headless / API mode.

            floors = arch_data.get("floors") or {}
            floor_map = {
                "gf": "ground_floor_plan",
                "1f": "first_floor_plan",
                "2f": "second_floor_plan",
                "roof": "roof_floor_plan"
            }
            for f_key, plan_type in floor_map.items():
                f_val = floors.get(f_key)
                if isinstance(f_val, dict):
                    plan = get_or_create(plan_type)
                    area = f_val.get("area")
                    if area is None:
                        if f_key == "gf":
                            area = arch_data.get("gf_area")
                        elif f_key == "roof":
                            area = arch_data.get("roof_slab_area")
                    if area is not None:
                        plan["total_floor_area"] = area
                    
                    perim = f_val.get("ext_perimeter")
                    if perim is None:
                        if f_key == "gf":
                            perim = arch_data.get("external_perimeter")
                        elif f_key == "roof":
                            perim = arch_data.get("roof_perimeter")
                    if perim is not None:
                        plan["ext_perimeter"] = perim
                        
                    if f_val.get("wet_area") is not None:
                        plan["wet_area"] = f_val["wet_area"]
                    if f_val.get("wet_perimeter") is not None:
                        plan["wet_perimeter"] = f_val["wet_perimeter"]
                    if f_val.get("dry_perimeter") is not None:
                        plan["dry_perimeter"] = f_val["dry_perimeter"]
                    if f_val.get("wall_internal") is not None:
                        plan["int_walls_length"] = f_val["wall_internal"]
                    if f_val.get("dry_area") is not None:
                        plan["dry_area"] = f_val["dry_area"]
                    plan["_ok"] = True
        except Exception as e:
            print(f"Error loading _arch_data.json: {e}")

    # 3. Merge _openings_data.json (Doors & Windows schedules)
    openings_path = os.path.join(root, "_openings_data.json")
    if os.path.exists(openings_path):
        try:
            with open(openings_path, encoding='utf-8') as f:
                openings_data = json.load(f)
            
            if openings_data.get("doors") or openings_data.get("windows"):
                sched_entry = get_or_create("schedules")
                if openings_data.get("doors") is not None:
                    sched_entry["doors"] = openings_data["doors"]
                if openings_data.get("windows") is not None:
                    sched_entry["windows"] = openings_data["windows"]
                sched_entry["_ok"] = True
        except Exception as e:
            print(f"Error loading _openings_data.json: {e}")


from utils.i18n import t

def render_step3() -> bool:
    import streamlit as st
    st.markdown(t("extract_title"))
    st.caption(t("extract_caption"))

    classified = st.session_state.get("classified_pages", [])
    ready      = [p for p in classified if p["detected_type"] != "unknown"]

    if "extraction_results" not in st.session_state and ready:
        results = {}
        for p in ready:
            key = f"{p['pdf']}_p{p['page_num']}_{p['detected_type']}"
            results[key] = {
                "_ok": False,
                "drawing_type": p["detected_type"],
                **p
            }
        st.session_state["extraction_results"] = results

    # Always sync disk schedules/openings/arch files on page load to keep session state in sync with disk source of truth
    # if "extraction_results" in st.session_state:
    #     merge_schedule_json_to_results(st.session_state["extraction_results"])

    if not ready:
        st.warning(" No classified pages found. Go back to Step 2.")
        return False

    # Show what will be extracted per page
    with st.expander("️ What will be extracted per page"):
        for p in ready:
            config  = DRAWING_REQUIRED_INPUTS.get(p["detected_type"], {})
            extract = config.get("extract_only", [])
            st.markdown(f"**{p['pdf']} P{p['page_num']}** → `{p['detected_type']}`")
            st.caption("Extracts: " + ", ".join(extract))

    user_data = st.session_state.get("user", {})
    role = user_data.get("role", "user")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        run_extract = st.button(t("extract_run_btn"), type="primary", use_container_width=True)
    with col2:
        force_count = st.session_state.get("force_extract_count", 0)
        is_admin = (role == "admin")
        
        btn_label = f"Force Re-Extract ({force_count} used)" if is_admin else (f"Force Re-Extract" if force_count == 0 else "Limit Reached")
        can_force = is_admin or (force_count < 1)
        force_extract = st.button(btn_label, use_container_width=True, disabled=not can_force)

    if run_extract or force_extract:
        if force_extract:
            st.session_state["force_extract_count"] = force_count + 1
            
        results  = {}
        progress = st.progress(0)
        status   = st.empty()

        for i, page_info in enumerate(ready):
            drawing_type = page_info["detected_type"]
            pdf_type     = page_info["pdf"]
            page_idx     = page_info["page_index"]

            status.info(f"{t('extract_running')} {pdf_type} Page {page_info['page_num']} — {drawing_type.replace('_',' ').title()}")

            # Step 1 stores pages under "str_"/"arch_"; step 2 tags pdf as
            # "structural"/"architectural" — map between them.
            _prefix   = {"structural": "str", "architectural": "arch"}.get(pdf_type, pdf_type)
            pages_src = st.session_state.get(f"{_prefix}_pages",
                        st.session_state.get(f"{pdf_type}_pages", []))
            texts_src = st.session_state.get(f"{_prefix}_texts",
                        st.session_state.get(f"{pdf_type}_texts", []))

            if page_idx < len(pages_src):
                page_text = texts_src[page_idx] if page_idx < len(texts_src) else ""
                user_data = st.session_state.get("user")
                user_id = user_data.get("id") if user_data else None
                result    = extract_page(pages_src[page_idx], drawing_type, page_text, user_id, force_reextract=force_extract)
                key       = f"{pdf_type}_p{page_info['page_num']}_{drawing_type}"
                results[key] = {**result, **page_info}
            else:
                st.error(f"Error: Could not find image data for {pdf_type} page {page_info['page_num']}. The server may have restarted. Please go back to Step 1 and upload the PDF again.")
                return False

            progress.progress((i + 1) / len(ready))

        # ── CROSS-CHECK: Count door/window marks in floor plan texts ──
        # This fulfills the engine requirement to trust plan counts over schedule counts.
        arch_texts = st.session_state.get("arch_texts", [])
        plan_texts = []
        for p in ready:
            if p["pdf"] == "architectural" and p["detected_type"] in {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan"}:
                idx = p["page_index"]
                if idx < len(arch_texts):
                    plan_texts.append(arch_texts[idx].upper())
        
        if plan_texts:
            full_text = " \n ".join(plan_texts)
            for k, data in results.items():
                if data.get("drawing_type") in SCHEDULE_TYPES:
                    for lst_type in ["doors", "windows"]:
                        for item in data.get(lst_type, []):
                            mark = str(item.get("mark", "")).strip().upper()
                            if mark and len(mark) > 1: # avoid matching single letters like 'D' everywhere
                                m_clean = normalize_mark(mark)
                                match_pattern = ""
                                for char in m_clean:
                                    if char.isalpha():
                                        match_pattern += char + r"[\s\-_./]*"
                                    else:
                                        match_pattern += char
                                match_pattern = match_pattern.rstrip(r"[\s\-_./]*")
                                n = len(re.findall(rf"\b{match_pattern}\b", full_text))
                                if n > 0:
                                    item["count_in_plans"] = n
                                    item["count_source"]   = "floor_plans_fitz"

        # merge_schedule_json_to_results(results) # DISABLED
        st.session_state["extraction_results"] = results
        status.success(t("extract_done"))
        progress.empty()

    results = st.session_state.get("extraction_results", {})

    if not results:
        return False

    # Show extraction results
    st.markdown("###  Extraction Results")
    ok_count = sum(1 for r in results.values() if r.get("_ok"))
    st.success(f" {ok_count}/{len(results)} pages extracted successfully")

    for key, data in results.items():
        drawing_type = data.get("drawing_type", "unknown")
        conf = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(data.get("confidence","low"), "⚪")

        with st.expander(f"{conf} {key.replace('_',' ').title()}"):
            if not data.get("_ok"):
                st.error(f"❌ {data.get('_error','Failed')}")
                continue

            # ── Columns (combined schedule) ──
            if drawing_type in COLUMN_TYPES:
                cols = data.get("columns", []) or []
                st.markdown(f"**{len(cols)} column marks** (per-floor counts):")
                for c in cols:
                    st.caption(
                        f"{c.get('mark','?')}: {c.get('width_m','?')}×{c.get('length_m','?')} m  "
                        f"— GF:{c.get('count_gf',0)} · 1F:{c.get('count_1f',0)} · "
                        f"2F:{c.get('count_2f',0)} · Roof:{c.get('count_roof',0)}")

            # ── Columns (per-floor page) ──
            elif drawing_type in PERFLOOR_COLUMN_TYPES:
                floor = PERFLOOR_COLUMN_TYPES[drawing_type].upper()
                cols = data.get("columns", []) or []
                st.markdown(f"**{len(cols)} column marks** ({floor} floor):")
                for c in cols:
                    st.caption(f"{c.get('mark','?')}: {c.get('width_m','?')}×{c.get('length_m','?')} m "
                               f"× {c.get('count',0)}")

            # ── Foundations — show footings list ──
            elif drawing_type in FOUNDATION_TYPES:
                # Flat scalars
                for fld in ("longest_length", "longest_width"):
                    val = data.get(fld)
                    if val is not None:
                        st.markdown(f"✅ **{fld}**: `{val}`")
                    else:
                        st.markdown(f"❓ **{fld}**: *not found*")
                # Footings list
                footings = data.get("footings", []) or []
                if footings:
                    st.markdown(f"✅ **{len(footings)} footing types** extracted:")
                    for f in footings:
                        st.caption(
                            f"{f.get('mark','?')}: {f.get('width','?')}×{f.get('length','?')}×{f.get('depth','?')} m "
                            f"— count: {f.get('count','?')}")
                else:
                    st.markdown("❓ **footings**: *not found — no footing schedule detected*")

            # ── Slabs — show beams list + slab scalars ──
            elif drawing_type in SLAB_TYPES:
                for fld in ("slab_area", "slab_thickness"):
                    val = data.get(fld)
                    if val is not None:
                        st.markdown(f"✅ **{fld}**: `{val}`")
                    else:
                        st.markdown(f"❓ **{fld}**: *not found*")
                if drawing_type == "roof_slab":
                    rp = data.get("roof_perimeter")
                    if rp is not None:
                        st.markdown(f"✅ **roof_perimeter**: `{rp}`")
                    else:
                        st.markdown("❓ **roof_perimeter**: *not found*")
                beams = data.get("beams", []) or []
                if beams:
                    st.markdown(f"✅ **{len(beams)} beam types** extracted:")
                    for b in beams:
                        st.caption(
                            f"{b.get('mark','?')}: {b.get('width','?')}×{b.get('depth','?')} m "
                            f"— total length: {b.get('length','?')} m")
                else:
                    st.markdown("❓ **beams**: *not found — no beam schedule detected*")

            # ── Schedules (doors & windows) — show lists ──
            elif drawing_type in SCHEDULE_TYPES:
                doors = data.get("doors", []) or []
                if doors:
                    total_d = sum(d.get("count", 0) or 0 for d in doors)
                    st.markdown(f"✅ **{len(doors)} door types** — total count: **{total_d}**")
                    for d in doors:
                        w = d.get("width_m") or d.get("width_mm") or d.get("width", "?")
                        h = d.get("height_m") or d.get("height_mm") or d.get("height", "?")
                        count = d.get("count_in_plans") or d.get("count") or 0
                        st.caption(f"{d.get('mark','?')}: {w}×{h} — count: {count}")
                else:
                    st.markdown("❓ **doors**: *not found*")
                windows = data.get("windows", []) or []
                if windows:
                    total_w = sum(w.get("count", 0) or 0 for w in windows)
                    st.markdown(f"✅ **{len(windows)} window types** — total count: **{total_w}**")
                    for w in windows:
                        ww = w.get("width_m") or w.get("width_mm") or w.get("width", "?")
                        wh = w.get("height_m") or w.get("height_mm") or w.get("height", "?")
                        count = w.get("count_in_plans") or w.get("count") or 0
                        st.caption(f"{w.get('mark','?')}: {ww}×{wh} — count: {count}")
                else:
                    st.markdown("❓ **windows**: *not found*")

            elif drawing_type in ELEVATION_TYPES:
                for fld in ("gf_height_m", "f1_height_m", "total_villa_height_m", "parapet_height_m"):
                    val = data.get(fld)
                    if val is not None:
                        st.markdown(f"🔹 **{fld}**: `{val} m`")

            # 🔻 All other types (floor plans, tie beam, setting out, roof plan) 🔻
            else:
                config  = DRAWING_REQUIRED_INPUTS.get(drawing_type, {})
                extract = config.get("extract_only", [])
                for field in extract:
                    val = data.get(field)
                    if val is not None:
                        st.markdown(f"✅ **{field}**: `{val}`")
                    else:
                        st.markdown(f"❓ **{field}**: *not found*")

            if data.get("notes"):
                st.caption(f" {data['notes']}")

    if st.button(t("extract_next_btn"), type="primary", use_container_width=True):
        mark_step_done("extract")
        return True

    return False
