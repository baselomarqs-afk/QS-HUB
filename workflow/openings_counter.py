"""
Deterministic doors/windows take-off from VECTOR architectural PDFs.

Strategy (proven to generalise across UAE consultants' drawing styles):
    1. PAGES  -> prefer the user-confirmed floor-plan & schedule pages when provided;
                 otherwise identify real floor plans (excluding notes/regulations,
                 cover/area sheets, elevations/sections) and real schedule sheets
                 (including elevation-style schedules where width & height are
                 drawn as separate dimension lines without an 'X').
    2. COUNTS -> count ONLY real opening marks (D1, D-02, MD1, SD1, W1, W-06,
                 CW1, SW1, V1 — plus glazed panels P1..P9 ONLY when confirmed on
                 a door/window/panel schedule sheet). Never match bare letters or
                 English words like AND, BED, NEW, REV, CAD, WWW, etc.
    3. SIZES  -> read W x H from schedule text when present; automatically run
                 focused AI Vision on schedule sheets when sizes are graphical /
                 separate CAD dimension lines (like Kayan-style schedules).
    4. AREA   -> sum(w * h * count) for windows + glazed panels; sum(count) for doors.
"""
import re
import fitz
from collections import defaultdict

# Valid UAE architectural opening mark prefixes (ordered longest-first for alternation)
_DOOR_PREFIXES = (
    "MD", "SD", "FD", "GD", "AD", "ED", "ID", "WD", "TD", "PD", "OD", "BD", "LD", "CD", "KD", "D",
)
_WIN_PREFIXES = (
    "CW", "KW", "SW", "AW", "FW", "LW", "RW", "TW", "VW", "BW", "DW", "LV", "EV", "W", "V",
)
_DOOR_PREFIX_SET = set(_DOOR_PREFIXES)
_WIN_PREFIX_SET = set(_WIN_PREFIXES)

_ALL_PREFIX_ALT = "|".join(sorted(_DOOR_PREFIXES + _WIN_PREFIXES, key=len, reverse=True))

# Strict opening mark: valid prefix + optional '-' or space + REQUIRED 1-2 digit number (1..99),
# bounded so it NEVER matches inside English words (AND4, BED, NEW, REV, WWW, CAD, etc.)
# or decimal numbers (1.50).
_MARK_RE = re.compile(
    rf"(?<![A-Z0-9.])({_ALL_PREFIX_ALT})[\-\s]?0*([1-9]\d?)(?![A-Z0-9.])",
    re.IGNORECASE,
)

# Glazed curtain-wall / facade panel marks (P1..P19, PANEL - 01):
# ONLY counted when confirmed on the door/window/panel schedule sheet so we never
# confuse parking/pipe/structural P-marks on other consultants' drawings.
_PANEL_MARK_RE = re.compile(
    r"(?<![A-Z0-9.])(?:PANEL\s*[\-:]\s*|P[\-\s]?)0*([1-9]\d?)(?![A-Z0-9.])",
    re.IGNORECASE,
)

# Explicit long-form labels on schedule sheets (e.g. "MAIN DOOR - 01", "DOOR - 02", "WINDOW - 01")
_LONG_SCHED_LABEL_RE = re.compile(
    r"\b(MAIN\s+DOOR|DOOR|WINDOW|PANEL)\s*[\-:]\s*0*([1-9]\d?)\b",
    re.IGNORECASE,
)

# A size pair like  4.20 X 3.60   /   2.50x2.60   /   3.60 × 1.20  or mm like 1200 x 2100
_SIZE_RE = re.compile(r"(\d{1,4}(?:\.\d{1,2})?)\s*[xX×\*]\s*(\d{1,4}(?:\.\d{1,2})?)")

_ROOM_KW = (
    "BEDROOM", "BED ", "MAJLIS", "KITCHEN", "TOILET", "LIVING", "DINING",
    "BATH", "MASTER", "STORE", "PANTRY", "LAUNDRY", "MAID", "DRESSING",
)

_LEVEL_MARKER_RE = re.compile(
    r"(?:F\.?F\.?L\.?|S\.?S\.?L\.?|T\.?O\.?S\.?|PARAPET\s+LEV\w*|GATE\s+LEVEL)"
    r"[\s.:=]*[+\-]?\s*\d+\.\d{1,2}",
    re.IGNORECASE,
)


def _norm(letter: str, number: str) -> str:
    """W-01 / W 1 / W01 -> canonical 'W1'. MD-01 -> 'MD1'."""
    return f"{letter.upper()}{int(number)}" if number else letter.upper()


def _is_window_mark(mark: str) -> bool:
    """Return True for windows, vents, curtain walls, and scheduled glass panels."""
    m = re.match(r"^([A-Z]+)\d+$", mark.upper())
    if not m:
        return mark.upper().startswith("W")
    pref = m.group(1)
    return pref in _WIN_PREFIX_SET or pref == "P"


def _page_text(page) -> str:
    return page.get_text("text")


def _parse_dim_pair(w_str: str, h_str: str) -> tuple[float, float] | None:
    try:
        w, h = float(w_str), float(h_str)
    except ValueError:
        return None
    if w > 20:
        w /= 1000.0
    if h > 20:
        h /= 1000.0
    if 0.2 <= w <= 12.0 and 0.2 <= h <= 12.0:
        return (round(w, 2), round(h, 2))
    return None


def classify_pages(doc) -> dict:
    """
    Split the document into roles using only the text layer.
      returns {'plan_pages':[idx...], 'schedule_pages':[idx...]}
    Excludes dense regulations/notes pages (>7000 chars), cover/area summary sheets,
    and elevation/section sheets. Detects both tabular (W x H) and elevation-style
    (DOOR - 02 / WINDOW - 01 / PANEL - 01) schedule sheets.
    """
    plan_pages, schedule_pages = [], []
    for i in range(len(doc)):
        raw = _page_text(doc[i])
        # Never treat massive regulation/notes pages (e.g., Dubai Green Building 30k chars) as plans
        if len(raw) > 7000:
            continue
        t = raw.upper()

        # Skip cover / approval / area-calculation / boundary-wall sheets
        if any(k in t for k in (
            "DUBAI GREEN BUILDING", "GREEN BUILDING REGULATIONS",
            "CIVIL DEFENCE APPROVAL", "PLOT COVERAGE ALLOWED",
            "AREA CALCULATION", "BUILT UP AREA SCHEDULE", "BUILT-UP AREA SCHEDULE",
            "STAIRS DETAILS", "STAIRS DETIALS", "FRONT ELEVATION BW",
            "BOUNDARY WALL ELEVATION", "SITE SECTIONS",
        )):
            continue

        marks = _MARK_RE.findall(t)
        rooms = sum(t.count(k) for k in _ROOM_KW)
        sizes = [p for a, b in _SIZE_RE.findall(t) if (p := _parse_dim_pair(a, b))]
        long_sched = _LONG_SCHED_LABEL_RE.findall(t)

        has_sched_header = bool(re.search(
            r"\b(?:DOOR\s*(?:&|AND|/)?\s*WINDOW\s+SCHEDULE|DOOR\s+SCHEDULE|WINDOW\s+SCHEDULE|"
            r"SCHEDULE\s+OF\s+(?:DOORS?|WINDOWS?|OPENINGS?)|DOORS?\s*(?:&|AND|/)\s*WINDOWS?\s+DETAILS?|"
            r"PANELS?\s*(?:&|AND)\s*DOORS?\s*(?:&|AND)\s*WINDOWS?|"
            r"DOORS?\s+DETAILS?|WINDOWS?\s+DETAILS?)\b",
            t,
        ))
        has_glazing_spec_sheet = (
            rooms < 3
            and any(k in t for k in ("POWDER COATED", "UPVC SECTIONS", "ALUMINIUM SECTIONS", "ALUMINUM SECTIONS"))
            and ("WINDOW" in t or "DOOR" in t)
        )
        is_schedule = (
            (len(sizes) >= 4 and any(kw in t for kw in ("WINDOW", "DOOR", "DETAIL", "SCHEDULE")))
            or (has_sched_header and rooms < 4)
            or (len(long_sched) >= 3 and rooms < 3)
            or has_glazing_spec_sheet
        )
        if is_schedule:
            schedule_pages.append(i)
            continue

        # Skip elevation & section sheets (multiple distinct vertical levels)
        lvl_vals = {
            re.search(r"\d+\.\d{1,2}", m).group(0)
            for m in _LEVEL_MARKER_RE.findall(t)
            if re.search(r"\d+\.\d{1,2}", m)
        }
        is_elev_or_section = (
            len(lvl_vals) >= 3
            or (len(lvl_vals) >= 2 and rooms < 4)
            or (bool(re.search(r"\b(?:SECTION\s*[\-\s]*(?:A[\-\s]*A|B[\-\s]*B|1[\-\s]*1)|ELEVATION\s+FINISHING)\b", t)) and len(marks) < 6)
        )
        if is_elev_or_section:
            continue

        # A real floor plan has opening marks AND (room words or multiple distinct floor-plan marks)
        if (rooms >= 2 and len(marks) >= 3) or len(marks) >= 6:
            plan_pages.append(i)
    return {"plan_pages": plan_pages, "schedule_pages": schedule_pages}


def _scheduled_panel_marks(doc, schedule_pages) -> set[str]:
    """Return {'P1', 'P2', ...} ONLY if the schedule sheet explicitly defines glazed PANEL items."""
    panels = set()
    for idx in schedule_pages:
        t = _page_text(doc[idx]).upper()
        if "PANEL" not in t:
            continue
        for m in _LONG_SCHED_LABEL_RE.finditer(t):
            if m.group(1).upper() == "PANEL":
                panels.add(f"P{int(m.group(2))}")
        for m in re.finditer(r"(?<![A-Z0-9.])P0*([1-9]\d?)(?![A-Z0-9.])", t):
            panels.add(f"P{int(m.group(1))}")
    return panels


def _size_anchors(words):
    """Find size pairs in a word list, returning [(cx, cy, w, h), ...].
    Handles sizes split across words: '4.20X' '3.60'  or  '4.20' 'X' '3.60'."""
    out = []
    n = len(words)
    for i in range(n):
        for span in (1, 2, 3):
            if i + span > n:
                break
            chunk = " ".join(w[4] for w in words[i:i + span])
            m = _SIZE_RE.search(chunk)
            if m:
                parsed = _parse_dim_pair(m.group(1), m.group(2))
                if not parsed:
                    break
                x0 = min(words[j][0] for j in range(i, i + span))
                y0 = min(words[j][1] for j in range(i, i + span))
                x1 = max(words[j][2] for j in range(i, i + span))
                y1 = max(words[j][3] for j in range(i, i + span))
                out.append(((x0 + x1) / 2, (y0 + y1) / 2, parsed[0], parsed[1]))
                break
    return out


def parse_sizes(doc, schedule_pages, known_marks=None, allowed_panels: set[str] | None = None) -> dict:
    """{mark -> (w_m, h_m)} from the schedule page text layer (including scheduled panels)."""
    sizes, src = {}, {}

    def _find_mark(text: str) -> str | None:
        mk = _MARK_RE.search(text)
        if mk:
            return _norm(mk.group(1), mk.group(2))
        if allowed_panels:
            pm = _PANEL_MARK_RE.search(text)
            if pm:
                pkey = f"P{int(pm.group(1))}"
                if pkey in allowed_panels:
                    return pkey
        return None

    for idx in schedule_pages:
        for block in doc[idx].get_text("blocks"):
            txt = block[4]
            # Split multi-line blocks by line so each row pairs with its own size
            for line in txt.splitlines():
                key = _find_mark(line)
                sz = _SIZE_RE.search(line)
                if key and sz:
                    parsed = _parse_dim_pair(sz.group(1), sz.group(2))
                    if parsed and key not in sizes:
                        sizes[key] = parsed
                        src[key] = "schedule"
            key = _find_mark(txt)
            sz = _SIZE_RE.search(txt)
            if key and sz and key not in sizes:
                parsed = _parse_dim_pair(sz.group(1), sz.group(2))
                if parsed:
                    sizes[key] = parsed
                    src[key] = "schedule"

    # Pass 2 — positional nearest-mark pairing for marks still missing a size.
    for idx in schedule_pages:
        words = doc[idx].get_text("words")
        marks = []
        for w in words:
            tok = w[4].strip()
            mm = _MARK_RE.fullmatch(tok)
            if mm:
                marks.append(((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, _norm(mm.group(1), mm.group(2))))
            elif allowed_panels:
                pm = _PANEL_MARK_RE.fullmatch(tok)
                if pm:
                    pkey = f"P{int(pm.group(1))}"
                    if pkey in allowed_panels:
                        marks.append(((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, pkey))
        if not marks:
            continue
        for sx, sy, w, h in _size_anchors(words):
            best_key, bd = None, 1e9
            for mx, my, mkey in marks:
                d = (mx - sx) ** 2 + (my - sy) ** 2
                if d < bd:
                    bd, best_key = d, mkey
            if best_key and best_key not in sizes:
                sizes[best_key] = (round(w, 2), round(h, 2))
                src[best_key] = "schedule"

    return sizes, src


def count_marks_by_page(doc, plan_pages, allowed_panels: set[str] | None = None) -> tuple[dict, dict]:
    """Return (total_counts, per_page_counts) across all real floor-plan pages."""
    totals = defaultdict(int)
    per_page = defaultdict(list)
    for idx in plan_pages:
        t = _page_text(doc[idx])
        page_c = defaultdict(int)
        for m in _MARK_RE.finditer(t):
            page_c[_norm(m.group(1), m.group(2))] += 1
        if allowed_panels:
            for pm in re.finditer(r"(?<![A-Z0-9.])P[\-\s]?0*([1-9]\d?)(?![A-Z0-9.])", t, re.IGNORECASE):
                pkey = f"P{int(pm.group(1))}"
                if pkey in allowed_panels:
                    page_c[pkey] += 1
        for k, v in page_c.items():
            totals[k] += v
            per_page[k].append(v)
    return dict(totals), dict(per_page)


def count_marks(doc, plan_pages, allowed_panels: set[str] | None = None) -> dict:
    """{mark -> total occurrences across all real floor-plan pages}."""
    totals, _ = count_marks_by_page(doc, plan_pages, allowed_panels=allowed_panels)
    return totals


_VISION_SIZE_PROMPT = (
    "This image is a UAE villa DOOR, WINDOW, and/or GLAZED PANEL SCHEDULE sheet. "
    "Each opening has a label such as W1, W-01, WINDOW - 01, P1, PANEL - 01, D1, D2, "
    "DOOR - 02, MD1, or MAIN DOOR - 01. "
    "Its overall WIDTH and HEIGHT may be printed as 'W x H' OR shown as separate "
    "horizontal (width) and vertical (height) dimension lines around each elevation drawing. "
    "Read EVERY labelled window, glazed panel, and door item and return ONLY JSON (no markdown): "
    '{"items":[{"mark":"W1","width_m":1.50,"height_m":3.84},{"mark":"P1","width_m":1.20,"height_m":7.78},{"mark":"D2","width_m":1.15,"height_m":2.28}]}. '
    "Normalize labels: 'WINDOW - 01' -> 'W1', 'PANEL - 01' -> 'P1', 'MAIN DOOR - 01' -> 'MD1', 'DOOR - 02' -> 'D2'. "
    "Read the exact printed width number directly above/below each opening (do not confuse neighboring widths) and the total glazing/opening height in METRES (divide by 1000 if printed in mm). "
    "Skip any item whose dimensions you cannot read clearly."
)


def _page_png_bytes(doc, idx, zoom: float = 2.2, max_side: int = 2400) -> bytes:
    import io
    from PIL import Image
    pix = doc[idx].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    w, h = img.size
    if max(w, h) > max_side:
        s = max_side / max(w, h)
        img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _normalize_vision_mark(raw_mark: str) -> str | None:
    s = (raw_mark or "").strip().upper()
    if not s:
        return None
    lm = _LONG_SCHED_LABEL_RE.search(s)
    if lm:
        kind, num = lm.group(1).upper(), lm.group(2)
        if "MAIN" in kind:
            return f"MD{int(num)}"
        if "DOOR" in kind:
            return f"D{int(num)}"
        if "WINDOW" in kind:
            return f"W{int(num)}"
        if "PANEL" in kind:
            return f"P{int(num)}"
    m = _MARK_RE.search(s)
    if m:
        return _norm(m.group(1), m.group(2))
    pm = _PANEL_MARK_RE.fullmatch(s)
    if pm:
        return f"P{int(pm.group(1))}"
    return None


def read_sizes_via_vision(doc, schedule_pages) -> dict:
    """{mark -> (w_m, h_m)} read VISUALLY off the schedule sheet image."""
    try:
        from utils.key_manager import get_key_manager
        from google import genai
        from google.genai import types
        import json as _json
    except Exception:
        return {}

    import time as _time
    mgr = get_key_manager()
    out: dict = {}
    for idx in schedule_pages:
        png = _page_png_bytes(doc, idx)
        for attempt in range(6):
            api_key, model = mgr.get_key_and_model()
            if not api_key or api_key == "NO_API_KEY_FOUND":
                return out
            try:
                client = genai.Client(api_key=api_key, http_options={"timeout": 60.0})
                resp = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(data=png, mime_type="image/png"),
                        types.Part.from_text(text=_VISION_SIZE_PROMPT),
                    ],
                )
                txt = re.sub(r"```json|```", "", resp.text or "").strip()
                m_json = re.search(r"\{.*\}", txt, re.DOTALL)
                data = _json.loads(m_json.group(0) if m_json else txt)
                for it in data.get("items", []):
                    key = _normalize_vision_mark(str(it.get("mark", "")))
                    if not key:
                        continue
                    w = float(it.get("width_m") or 0)
                    h = float(it.get("height_m") or 0)
                    if w > 20:
                        w /= 1000.0
                    if h > 20:
                        h /= 1000.0
                    # Villa openings & double-height facade glass panels can reach 12m
                    if 0.2 <= w <= 12.0 and 0.2 <= h <= 12.0 and key not in out:
                        out[key] = (round(w, 2), round(h, 2))
                break  # page done
            except Exception as e:
                err = str(e)
                low = err.lower()
                if "404" in low or "no longer available" in low:
                    if hasattr(mgr, "mark_model_unavailable"):
                        mgr.mark_model_unavailable(model)
                    continue
                transient = any(k in low for k in ("429", "503", "unavailable", "resource_exhausted", "overloaded"))
                if transient:
                    try:
                        mgr.mark_rate_limited(api_key, model)
                    except Exception:
                        pass
                    _time.sleep(0.5)
                    continue
                print(f"[openings_counter vision] {err}")
                break
    return out


def extract_openings(
    pdf_path: str,
    use_vision: bool = False,
    plan_pages_override: list[int] | None = None,
    schedule_pages_override: list[int] | None = None,
) -> dict | None:
    """
    Returns {'windows':[...], 'doors':[...], 'totals':{...}, '_ok':True,
             '_source':'vector_text'} or None when no text layer is usable.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None

    roles = classify_pages(doc)
    if plan_pages_override:
        valid_plans = [p for p in plan_pages_override if 0 <= p < len(doc)]
        if valid_plans:
            roles["plan_pages"] = valid_plans
    if schedule_pages_override:
        valid_sched = [p for p in schedule_pages_override if 0 <= p < len(doc)]
        if valid_sched:
            roles["schedule_pages"] = sorted(set(roles["schedule_pages"] + valid_sched))

    # Never count opening labels on the schedule sheet itself.
    count_pages = [p for p in roles["plan_pages"] if p not in roles["schedule_pages"]]
    if not count_pages:
        doc.close()
        return None

    allowed_panels = _scheduled_panel_marks(doc, roles["schedule_pages"])
    counts, per_page_counts = count_marks_by_page(doc, count_pages, allowed_panels=allowed_panels)
    if not counts:
        doc.close()
        return None

    sizes, src = parse_sizes(doc, roles["schedule_pages"], known_marks=list(counts), allowed_panels=allowed_panels)

    # Visual fill-in for ANY window/panel/door mark whose size couldn't be read from text.
    missing_marks = [m for m in counts if m not in sizes]
    if use_vision and missing_marks and roles["schedule_pages"]:
        vis = read_sizes_via_vision(doc, roles["schedule_pages"])
        for m in missing_marks:
            if m in vis:
                sizes[m] = vis[m]
                src[m] = "vision"

    roles["count_pages"] = count_pages
    doc.close()

    windows, doors = [], []
    for mark, cnt in sorted(counts.items()):
        w, h = sizes.get(mark, (0.0, 0.0))
        page_hits = per_page_counts.get(mark, [])
        count_source = "plan_label_count"
        # Architectural rule: a continuous multi-storey curtain-wall panel or double-height
        # glazing unit (height > 5.0 m) is tagged on EACH floor plan it passes through.
        # Summing across floors would double-count its full 2-storey area, so take max per floor.
        if h > 5.0 and len(page_hits) >= 2:
            cnt = max(page_hits)
            count_source = "plan_label_count_multifloor"
        rec = {
            "mark": mark,
            "width_m": w,
            "height_m": h,
            "count": cnt,
            "count_source": count_source,
            "size_source": src.get(mark, "missing"),
        }
        (windows if _is_window_mark(mark) else doors).append(rec)

    win_area = round(sum(r["width_m"] * r["height_m"] * r["count"] for r in windows), 2)
    door_total = sum(r["count"] for r in doors)

    return {
        "windows": windows,
        "doors": doors,
        "totals": {
            "window_area": win_area,
            "window_count": sum(r["count"] for r in windows),
            "door_count": door_total,
        },
        "_ok": True,
        "_source": "vector_text",
        "_pages": roles,
    }


def extract_openings_for_project(
    project_cache: str,
    use_vision: bool = True,
    classified_pages: list[dict] | None = None,
    arch_boundaries: list[dict] | None = None,
) -> dict | None:
    """
    Run the take-off over every architectural PDF cached for a project (arch_*.pdf)
    and merge the result. Uses user-verified `classified_pages` (when supplied) so
    notes/sections/elevations are NEVER mistakenly counted and schedule sheets are
    ALWAYS read for window/panel/door dimensions.
    """
    import os, glob
    arch_pdfs = sorted(glob.glob(os.path.join(project_cache, "arch_*.pdf")))
    if not arch_pdfs:
        return None

    # Map global architectural page_index -> (pdf_basename, local_page_idx)
    plan_by_pdf: dict[str, list[int]] = defaultdict(list)
    sched_by_pdf: dict[str, list[int]] = defaultdict(list)
    if classified_pages:
        _PLAN_TYPES = {"ground_floor_plan", "first_floor_plan", "second_floor_plan"}
        _SCHED_TYPES = {"schedules", "door_schedule", "window_schedule", "arch_doors", "arch_windows"}
        for p in classified_pages:
            if p.get("pdf") != "architectural":
                continue
            dt = p.get("detected_type") or ""
            gidx = p.get("page_index")
            if gidx is None:
                continue
            pdf_name = os.path.basename(arch_pdfs[0])
            local_idx = int(gidx)
            if arch_boundaries:
                for b in arch_boundaries:
                    if b["start"] <= gidx <= b["end"]:
                        pdf_name = os.path.basename(b["pdf_path"])
                        local_idx = int(gidx) - int(b["start"])
                        break
            if dt in _PLAN_TYPES:
                plan_by_pdf[pdf_name].append(local_idx)
            elif dt in _SCHED_TYPES:
                sched_by_pdf[pdf_name].append(local_idx)

    windows: dict = {}
    doors: dict = {}
    pages_used = []
    for pdf in arch_pdfs:
        bname = os.path.basename(pdf)
        r = extract_openings(
            pdf,
            use_vision=use_vision,
            plan_pages_override=plan_by_pdf.get(bname) or None,
            schedule_pages_override=sched_by_pdf.get(bname) or None,
        )
        if not r or not r.get("_ok"):
            continue
        pages_used.append({bname: r.get("_pages")})
        for rec in r["windows"]:
            cur = windows.get(rec["mark"])
            if not cur:
                windows[rec["mark"]] = dict(rec)
            else:
                cur["count"] += rec["count"]
                if cur.get("size_source") in (None, "missing") and rec.get("size_source") != "missing":
                    cur["width_m"], cur["height_m"] = rec["width_m"], rec["height_m"]
                    cur["size_source"] = rec["size_source"]
        for rec in r["doors"]:
            cur = doors.get(rec["mark"])
            if not cur:
                doors[rec["mark"]] = dict(rec)
            else:
                cur["count"] += rec["count"]
                if cur.get("size_source") in (None, "missing") and rec.get("size_source") != "missing":
                    cur["width_m"], cur["height_m"] = rec["width_m"], rec["height_m"]
                    cur["size_source"] = rec["size_source"]

    if not windows and not doors:
        return None

    win_list = sorted(windows.values(), key=lambda r: r["mark"])
    door_list = sorted(doors.values(), key=lambda r: r["mark"])
    win_area = round(sum(w["width_m"] * w["height_m"] * w["count"] for w in win_list), 2)
    needs_review = any(
        w.get("size_source") == "missing" or (w.get("width_m", 0) == 0 or w.get("height_m", 0) == 0)
        for w in win_list
    )

    return {
        "windows": win_list,
        "doors": door_list,
        "totals": {
            "window_area": win_area,
            "window_count": sum(w["count"] for w in win_list),
            "door_count": sum(d["count"] for d in door_list),
        },
        "_ok": True,
        "_source": "vector_text",
        "_needs_size_review": needs_review,
        "_pages": pages_used,
    }


# ── CLI test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    sys.stdout.reconfigure(encoding="utf-8")
    res = extract_openings(sys.argv[1])
    print(json.dumps(res, ensure_ascii=False, indent=2))
