"""
Auto-classifies every page of an STR or ARCH PDF into a typed category.

Strategy (cheapest path first):
    1. Try fitz text — look for keywords in the page text (free, fast).
    2. If page has no text OR text didn't match, fall back to AI Vision.

Outputs JSON file with structure:
    {
      "<pdf_path>": {
        "0": {"type": "foundation",     "source": "fitz", "confidence": 0.95},
        "1": {"type": "tie_beam",       "source": "fitz", "confidence": 0.85},
        "2": {"type": "column_schedule","source": "AI", "confidence": 0.90},
        ...
      }
    }

Usage:
    py _page_classifier_ai.py path/to/STR.pdf [path/to/ARCH.pdf]
"""
import sys, os, json
import fitz

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from _pdf_utils import render_page, ask_ai, parse_json, pdf_page_count

OUT_JSON = os.path.join(os.path.dirname(__file__), "_page_classification.json")

# ── Page types ────────────────────────────────────────────────────────────────
PAGE_TYPES = [
    "foundation",        # Foundation layout (footings plan + SCHEDULE OF FOOTINGS)
    "tie_beam",          # Tie beam layout + SCHEDULE OF TIE BEAMS
    "column_schedule",   # SCHEDULE OF COLUMNS (or column layout with schedule)
    "slab_1f",           # 1st floor slab/beam layout
    "slab_2f",           # 2nd floor slab/beam layout (if exists)
    "slab_roof",         # Roof slab/beam layout
    "arch_site",         # Site / setting-out / plot plan
    "arch_gf",           # Ground floor architectural plan
    "arch_1f",           # 1st floor architectural plan
    "arch_2f",           # 2nd floor architectural plan (if exists)
    "arch_roof",         # Roof architectural plan
    "arch_elevation",    # Elevation / facade
    "arch_section",      # Building section
    "door_schedule",     # SCHEDULE OF DOORS table
    "window_schedule",   # SCHEDULE OF WINDOWS table
    "unknown",
]


# ── Fitz-based fast classifier ────────────────────────────────────────────────
# Each rule: (page_type, keywords_required_ANY_match, optional_extra_score_keywords)
_FITZ_RULES = [
    ("foundation",      ["SCHEDULE OF FOOTING", "FOUNDATION LAYOUT", "FOUNDATION PLAN"], ["F1", "F2"]),
    ("tie_beam",        ["SCHEDULE OF TIE BEAM", "TIE BEAM LAYOUT", "TIE BEAM PLAN"],    ["TB1", "TB2"]),
    ("column_schedule", ["SCHEDULE OF COLUMN", "COLUMN SCHEDULE"],                       ["C1", "C2"]),
    ("slab_1f",         ["1ST FLOOR SLAB", "FIRST FLOOR SLAB", "1ST FLOOR BEAM",
                         "FIRST FLOOR BEAM", "1ST FLR SLAB"],                            ["B1", "B2"]),
    ("slab_2f",         ["2ND FLOOR SLAB", "SECOND FLOOR SLAB", "2ND FLOOR BEAM"],       ["B1", "B2"]),
    ("slab_roof",       ["ROOF SLAB", "ROOF FLOOR BEAM", "ROOF FLOOR SLAB",
                         "ROOF BEAM LAYOUT"],                                            ["B1", "HB1"]),
    ("arch_site",       ["SITE PLAN", "SETTING OUT", "PLOT PLAN", "LOCATION PLAN"],      []),
    ("arch_gf",         ["GROUND FLOOR PLAN", "G.F PLAN", "GF PLAN"],                    []),
    ("arch_1f",         ["FIRST FLOOR PLAN", "1ST FLOOR PLAN", "1ST FLR PLAN"],          []),
    ("arch_2f",         ["SECOND FLOOR PLAN", "2ND FLOOR PLAN"],                         []),
    ("arch_roof",       ["ROOF PLAN", "ROOF LAYOUT"],                                    []),
    ("arch_elevation",  ["ELEVATION", "FRONT VIEW", "SIDE VIEW", "REAR ELEVATION"],      []),
    ("arch_section",    ["SECTION A-A", "SECTION B-B", "CROSS SECTION"],                 []),
    ("door_schedule",   ["DOOR SCHEDULE", "SCHEDULE OF DOOR"],                           ["D1", "D2"]),
    ("window_schedule", ["WINDOW SCHEDULE", "SCHEDULE OF WINDOW"],                       ["W1", "W2"]),
]


def classify_with_fitz(pdf_path: str, page_index: int) -> tuple[str, float]:
    """
    Fast fitz-based classifier. Returns (page_type, confidence 0-1).
    Returns ('unknown', 0.0) if no rule matches.
    """
    doc  = fitz.open(pdf_path)
    try:
        text = doc[page_index].get_text("text").upper()
    finally:
        doc.close()

    if len(text.strip()) < 30:
        return "unknown", 0.0   # likely scanned page

    best_type, best_score = "unknown", 0.0
    for ptype, primary, extras in _FITZ_RULES:
        score = 0.0
        for kw in primary:
            if kw in text:
                score = max(score, 0.85)   # primary keyword match
        if score > 0:
            for kw in extras:
                if kw in text:
                    score = min(0.99, score + 0.03)
            if score > best_score:
                best_type, best_score = ptype, score
    return best_type, round(best_score, 2)


# ── AI-based classifier (fallback for unknown pages) ──────────────────────
_CLASSIFICATION_PROMPT = f"""You are classifying a page of a UAE villa construction PDF.

Look at the drawing and identify what type of page this is.
Possible types are EXACTLY one of these (choose the closest match):
    {", ".join(PAGE_TYPES)}

Guidelines:
- "foundation"      → footings layout / SCHEDULE OF FOOTINGS table
- "tie_beam"        → tie beam plan / SCHEDULE OF TIE BEAMS
- "column_schedule" → SCHEDULE OF COLUMNS table or column key plan
- "slab_1f"         → 1st floor slab/beam layout
- "slab_2f"         → 2nd floor slab/beam layout
- "slab_roof"       → roof slab/beam layout
- "arch_site"       → site plan / plot boundary / setting-out
- "arch_gf"         → ground floor architectural plan (rooms shown)
- "arch_1f"         → 1st floor architectural plan
- "arch_2f"         → 2nd floor architectural plan
- "arch_roof"       → roof architectural plan
- "arch_elevation"  → building elevation/facade (vertical view)
- "arch_section"    → building section (cut-through vertical view)
- "door_schedule"   → table of door types and sizes
- "window_schedule" → table of window types and sizes
- "unknown"         → none of the above

Return ONLY this JSON:
{{
  "type": "<one of the types above>",
  "confidence": 0.0-1.0,
  "rationale": "<one short sentence explaining your choice>"
}}
"""


def classify_with_AI(pdf_path: str, page_index: int, api_key: str | None = None) -> dict:
    """
    AI Vision fallback. Renders page at low DPI (180) for speed
    (we don't need to read fine details, just identify what kind of page it is).
    """
    img = render_page(pdf_path, page_index, dpi=180)
    raw = ask_ai(img, _CLASSIFICATION_PROMPT, api_key=api_key)
    try:
        parsed = parse_json(raw)
        ptype  = parsed.get("type", "unknown")
        if ptype not in PAGE_TYPES:
            ptype = "unknown"
        return {
            "type":       ptype,
            "confidence": float(parsed.get("confidence", 0.5)),
            "rationale":  parsed.get("rationale", ""),
        }
    except Exception as e:
        return {"type": "unknown", "confidence": 0.0, "rationale": f"parse error: {e}"}


# ── Main classifier ───────────────────────────────────────────────────────────
def classify_pdf(pdf_path: str, api_key: str | None = None,
                 fitz_min_confidence: float = 0.80) -> dict:
    """
    Classify every page of a PDF.

    Returns dict { "<page_index_str>": {"type", "source", "confidence", "rationale"} }
    """
    n_pages = pdf_page_count(pdf_path)
    result  = {}
    print(f"\n  Classifying {n_pages} pages of {os.path.basename(pdf_path)}...")

    for i in range(n_pages):
        ptype, conf = classify_with_fitz(pdf_path, i)
        if ptype != "unknown" and conf >= fitz_min_confidence:
            result[str(i)] = {
                "type":       ptype,
                "source":     "fitz",
                "confidence": conf,
                "rationale":  "fitz keyword match",
            }
            print(f"    page {i+1:2d} → {ptype:18s} [fitz {conf:.2f}]")
        else:
            try:
                g = classify_with_AI(pdf_path, i, api_key=api_key)
                result[str(i)] = {
                    "type":       g["type"],
                    "source":     "AI",
                    "confidence": g["confidence"],
                    "rationale":  g["rationale"],
                }
                print(f"    page {i+1:2d} → {g['type']:18s} [AI {g['confidence']:.2f}]  {g['rationale'][:60]}")
            except Exception as e:
                result[str(i)] = {
                    "type":       "unknown",
                    "source":     "error",
                    "confidence": 0.0,
                    "rationale":  str(e),
                }
                print(f"    page {i+1:2d} → ERROR: {e}")
    return result


def classify_and_save(pdf_paths: list[str], api_key: str | None = None) -> dict:
    """Classify multiple PDFs and persist to _page_classification.json."""
    out = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, encoding="utf-8") as f:
                out = json.load(f)
        except Exception:
            out = {}
    for path in pdf_paths:
        out[path] = classify_pdf(path, api_key=api_key)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved classification → {OUT_JSON}")
    return out


def get_pages_of_type(classification: dict, pdf_path: str, page_type: str) -> list[int]:
    """Helper: returns sorted list of 0-based page indices for a given type."""
    pdf_class = classification.get(pdf_path, {})
    return sorted(
        int(idx) for idx, info in pdf_class.items()
        if info.get("type") == page_type
    )


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py _page_classifier_ai.py path/to/STR.pdf [path/to/ARCH.pdf]")
        sys.exit(1)
    paths = sys.argv[1:]
    for p in paths:
        if not os.path.exists(p):
            print(f"ERROR: file not found: {p}")
            sys.exit(1)
    classify_and_save(paths)
