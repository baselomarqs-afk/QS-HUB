"""
Deterministic doors/windows take-off from VECTOR architectural PDFs.

Strategy (proven to generalise across consultants' drawing styles):
    1. SIZES  → read each mark's width×height from the door/window *schedule*
                page (text blocks: a mark label sits next to its "W x H" size).
    2. COUNTS → count how many times each mark (W-01, D3, …) is printed on the
                actual floor-PLAN pages.  The schedule rarely carries a reliable
                QTY column, but every opening is labelled on the plan, so the
                count is the number of label occurrences across all plan pages.
    3. AREA   → Σ (w · h · count) for windows; Σ count for doors.

No AI, no image guessing — works wherever the PDF text layer exists.
Falls back to None when the page has no usable text (scanned sheet) so the
caller can use the AI/vision path instead.
"""
import re
import fitz
from collections import defaultdict

# A drawing mark: e.g. W1, D1, CW1, KW, V1, DW1, SD1, FD1, AD1, GD1, MD1
_MARK_RE = re.compile(r"\b([A-Z]{0,2}[WDV])[\-\s]?0*(\d{0,2})\b", re.IGNORECASE)
# A size pair like  4.20 X 3.60   /   2.50x2.60   /   3.60 × 1.20
_SIZE_RE = re.compile(r"(\d{1,2}\.\d{1,2})\s*[xX×\*]\s*(\d{1,2}\.\d{1,2})")
_ROOM_KW = ("BED", "MAJLIS", "KITCHEN", "TOILET", "LIVING", "DINING",
            "BATH", "MASTER", "STORE", "PANTRY", "LAUNDRY", "MAID")


def _norm(letter: str, number: str) -> str:
    """W-01 / W 1 / W01  ->  canonical 'W1'. KW -> 'KW'."""
    return f"{letter.upper()}{int(number)}" if number else letter.upper()


def _page_text(page) -> str:
    return page.get_text("text")


def classify_pages(doc) -> dict:
    """
    Split the document into roles using only the text layer.
      returns {'plan_pages':[idx...], 'schedule_pages':[idx...]}
    A *plan* page has room words AND several marks.
    A *schedule* page is the one richest in size pairs (W x H).
    """
    plan_pages, schedule_pages = [], []
    for i in range(len(doc)):
        t = _page_text(doc[i]).upper()
        marks = _MARK_RE.findall(t)
        rooms = sum(t.count(k) for k in _ROOM_KW)
        sizes = _SIZE_RE.findall(t)
        is_schedule = (len(sizes) >= 4 and
                       any(kw in t for kw in ("WINDOW", "DOOR", "DETAIL", "SCHEDULE")))
        if is_schedule:
            schedule_pages.append(i)
        # A floor plan has rooms and several marks but is NOT a schedule sheet.
        if rooms >= 3 and len(marks) >= 4 and not is_schedule:
            plan_pages.append(i)
    return {"plan_pages": plan_pages, "schedule_pages": schedule_pages}


def _size_anchors(words):
    """Find size pairs in a word list, returning [(cx, cy, w, h), ...].
    Handles sizes split across words: '4.20X' '3.60'  or  '4.20' 'X' '3.60'."""
    out = []
    n = len(words)
    for i in range(n):
        # join this word with up to the next 2 words and test for a size pair
        for span in (1, 2, 3):
            if i + span > n:
                break
            chunk = " ".join(w[4] for w in words[i:i + span])
            m = _SIZE_RE.search(chunk)
            if m:
                x0 = min(words[j][0] for j in range(i, i + span))
                y0 = min(words[j][1] for j in range(i, i + span))
                x1 = max(words[j][2] for j in range(i, i + span))
                y1 = max(words[j][3] for j in range(i, i + span))
                out.append(((x0 + x1) / 2, (y0 + y1) / 2,
                            float(m.group(1)), float(m.group(2))))
                break
    return out


def parse_sizes(doc, schedule_pages, known_marks=None) -> dict:
    """{mark -> (w_m, h_m)} from the schedule page.

    Pass 1: a text *block* that contains both a mark and a size (tabular sheets).
    Pass 2: pair every size to the spatially NEAREST mark label (pictorial sheets
            where the mark and its size sit in separate text fragments).
    Pass 3: when the schedule's mark labels are graphics (no text), map the
            sizes — read in sheet order — onto the known marks in numeric order.
    """
    sizes, src = {}, {}
    for idx in schedule_pages:
        for block in doc[idx].get_text("blocks"):
            txt = block[4]
            mk = _MARK_RE.search(txt)
            sz = _SIZE_RE.search(txt)
            if mk and sz:
                key = _norm(mk.group(1), mk.group(2))
                if key not in sizes:
                    sizes[key] = (round(float(sz.group(1)), 2), round(float(sz.group(2)), 2))
                    src[key] = "schedule"

    # Pass 2 — positional nearest-mark pairing for marks still missing a size.
    for idx in schedule_pages:
        words = doc[idx].get_text("words")
        marks = [((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, _MARK_RE.fullmatch(w[4].strip()))
                 for w in words if _MARK_RE.fullmatch(w[4].strip())]
        if not marks:
            continue
        for sx, sy, w, h in _size_anchors(words):
            best, bd = None, 1e9
            for mx, my, mm in marks:
                d = (mx - sx) ** 2 + (my - sy) ** 2
                if d < bd:
                    bd, best = d, mm
            if best:
                key = _norm(best.group(1), best.group(2))
                if key not in sizes:
                    sizes[key] = (round(w, 2), round(h, 2))
                    src[key] = "schedule"

    # NOTE: no order/sequence guessing. A size is only accepted when it is
    # physically tied to its mark (same text block, or the spatially nearest
    # mark label). Marks whose label is a graphic carry no size here and are
    # filled later by a focused visual read of the schedule sheet.
    return sizes, src


def count_marks(doc, plan_pages) -> dict:
    """{mark -> total occurrences across all plan pages}."""
    counts = defaultdict(int)
    for idx in plan_pages:
        t = _page_text(doc[idx])
        for m in _MARK_RE.finditer(t):
            counts[_norm(m.group(1), m.group(2))] += 1
    return dict(counts)


_VISION_SIZE_PROMPT = (
    "This image is a WINDOW and/or DOOR SCHEDULE from a UAE villa drawing. "
    "Each item has a label such as W-01, W1, D-01 or D1 and a size written as "
    "WIDTH x HEIGHT in metres (e.g. \"2.50 X 3.60 M\"). "
    "Read EVERY labelled item and return ONLY JSON (no markdown): "
    '{"items":[{"mark":"W1","width_m":2.5,"height_m":3.6}]}. '
    "Use the exact width and height printed under/next to each label. "
    "Skip any label you cannot read with confidence."
)


def _page_png_bytes(doc, idx, zoom: float = 2.0, max_side: int = 1700) -> bytes:
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


def read_sizes_via_vision(doc, schedule_pages) -> dict:
    """{mark -> (w_m, h_m)} read VISUALLY off the schedule sheet image.

    Used only for marks whose label is a graphic (no text layer) — a narrow,
    reliable task (read the size printed under each labelled window/door). This
    reads the real drawing; it is NOT an order/sequence assumption.
    Returns {} when no API key is configured (caller keeps deterministic data).
    """
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
        # Retry with key/model rotation on transient overload (429/503/UNAVAILABLE).
        for attempt in range(6):
            api_key, model = mgr.get_key_and_model()
            if not api_key or api_key == "NO_API_KEY_FOUND":
                return out
            try:
                client = genai.Client(api_key=api_key)
                resp = client.models.generate_content(
                    model=model,
                    contents=[types.Part.from_bytes(data=png, mime_type="image/png"),
                              types.Part.from_text(text=_VISION_SIZE_PROMPT)],
                )
                txt = re.sub(r"```json|```", "", resp.text or "").strip()
                data = _json.loads(txt)
                for it in data.get("items", []):
                    m = _MARK_RE.search(str(it.get("mark", "")))
                    if not m:
                        continue
                    key = _norm(m.group(1), m.group(2))
                    w = float(it.get("width_m") or 0)
                    h = float(it.get("height_m") or 0)
                    if w > 20:
                        w /= 1000.0
                    if h > 20:
                        h /= 1000.0
                    # Plausibility gate: a real villa opening is 0.2–12 m on each
                    # side. Anything outside is a vision misread — drop it so the
                    # mark stays flagged for review instead of poisoning the area.
                    if 0.2 <= w <= 12 and 0.2 <= h <= 12 and key not in out:
                        out[key] = (round(w, 2), round(h, 2))
                break  # page done
            except Exception as e:
                err = str(e)
                transient = any(k in err for k in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded"))
                if transient:
                    try:
                        mgr.mark_rate_limited(api_key, model)
                    except Exception:
                        pass
                    _time.sleep(0.8)
                    continue
                print(f"[openings_counter vision] {err}")
                break
    return out


def extract_openings(pdf_path: str, use_vision: bool = False) -> dict | None:
    """
    Returns {'windows':[...], 'doors':[...], 'totals':{...}, '_ok':True,
             '_source':'vector_text'} or None when no text layer is usable.

    Counting is always deterministic (plan label occurrences). Sizes come from
    the schedule text; when a mark's label is a graphic and use_vision=True, the
    size is read visually off the schedule sheet (never guessed by order).
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None

    roles = classify_pages(doc)
    # Never count opening labels on the schedule sheet itself — it lists every
    # mark once and would inflate the real plan counts.
    count_pages = [p for p in roles["plan_pages"] if p not in roles["schedule_pages"]]
    if not count_pages:
        doc.close()
        return None

    counts = count_marks(doc, count_pages)
    if not counts:
        doc.close()
        return None
    sizes, src = parse_sizes(doc, roles["schedule_pages"], known_marks=list(counts))

    # Visual fill-in for window marks whose size couldn't be read from text.
    missing_win = [m for m in counts if m.startswith("W") and m not in sizes]
    if use_vision and missing_win and roles["schedule_pages"]:
        vis = read_sizes_via_vision(doc, roles["schedule_pages"])
        for m in missing_win:
            if m in vis:
                sizes[m] = vis[m]
                src[m] = "vision"

    roles["count_pages"] = count_pages
    doc.close()

    windows, doors = [], []
    for mark, cnt in sorted(counts.items()):
        w, h = sizes.get(mark, (0.0, 0.0))
        rec = {"mark": mark, "width_m": w, "height_m": h, "count": cnt,
               "count_source": "plan_label_count",
               "size_source": src.get(mark, "missing")}
        (windows if mark.startswith("W") else doors).append(rec)

    win_area = round(sum(r["width_m"] * r["height_m"] * r["count"] for r in windows), 2)
    door_total = sum(r["count"] for r in doors)

    return {
        "windows": windows,
        "doors": doors,
        "totals": {"window_area": win_area, "window_count": sum(r["count"] for r in windows),
                   "door_count": door_total},
        "_ok": True,
        "_source": "vector_text",
        "_pages": roles,
    }


def extract_openings_for_project(project_cache: str, use_vision: bool = True) -> dict | None:
    """
    Run the take-off over every architectural PDF cached for a project (files
    named arch_*.pdf in the project cache) and merge the result.  Counting is
    deterministic; window sizes that aren't in the text are read visually off
    the schedule sheet (use_vision).

    Returns the same shape as extract_openings(), or None if nothing usable.
    """
    import os, glob
    arch_pdfs = sorted(glob.glob(os.path.join(project_cache, "arch_*.pdf")))
    if not arch_pdfs:
        return None

    windows: dict = {}
    doors: dict = {}
    pages_used = []
    for pdf in arch_pdfs:
        r = extract_openings(pdf, use_vision=use_vision)
        if not r or not r.get("_ok"):
            continue
        pages_used.append({os.path.basename(pdf): r.get("_pages")})
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

    if not windows and not doors:
        return None

    win_list = sorted(windows.values(), key=lambda r: r["mark"])
    door_list = sorted(doors.values(), key=lambda r: r["mark"])
    win_area = round(sum(w["width_m"] * w["height_m"] * w["count"] for w in win_list), 2)
    # Flag only windows whose size could NOT be read at all (no text, no vision).
    # These have area 0 and genuinely need the user to fill the size.
    needs_review = any(w.get("size_source") == "missing" or
                       (w.get("width_m", 0) == 0 or w.get("height_m", 0) == 0)
                       for w in win_list)

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
