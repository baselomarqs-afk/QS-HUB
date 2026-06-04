"""
Extracts DOOR SCHEDULE and WINDOW SCHEDULE tables from the ARCH PDF
(or any PDF flagged with type=door_schedule / window_schedule by the classifier).

Output → _openings_data.json with structure:
{
  "doors": [
    {"mark":"D1","width_mm":900,"height_mm":2100,"count":4,"type":"single leaf wooden"},
    ...
  ],
  "windows": [
    {"mark":"W1","width_mm":1200,"height_mm":1500,"count":6,"type":"aluminum sliding"},
    ...
  ],
  "totals": {
    "door_count":      28,
    "window_count":    22,
    "window_area_m2":  41.6,
    "door_area_m2":    52.9
  }
}

The fitz pass also runs per-mark counts across floor plans for cross-validation:
if the schedule says D1 × 4 but the GF + 1F plans only show 3 'D1' labels,
we emit a warning.

Usage:
    py _read_openings_ai.py path/to/ARCH.pdf [api_key]
"""
import sys, os, json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from _pdf_utils import render_page, ask_ai, parse_json, count_token_in_page
from _page_classifier_ai import (
    classify_and_save, OUT_JSON as CLASS_JSON,
)

OUT_JSON = os.path.join(os.path.dirname(__file__), "_openings_data.json")


# ── Prompts ───────────────────────────────────────────────────────────────────
_DOOR_PROMPT = """This is a DOOR SCHEDULE for a UAE villa.
Extract every row of the door schedule table.

Return ONLY this JSON (no markdown, no explanation):
{
  "doors": [
    {"mark":"D1","width_mm":900,"height_mm":2100,"count":4,"type":"single leaf wooden"},
    {"mark":"D2","width_mm":1800,"height_mm":2400,"count":1,"type":"double leaf entry"},
    ...
  ]
}

Rules:
- mark = door identifier (D1, D2, MD, etc.)
- width_mm × height_mm = clear opening size in millimeters (convert from cm if needed)
- count = number of that door type used in the building
- type = short description (e.g. "single leaf wooden", "sliding glass", "fire-rated steel")
- Include ALL rows from the schedule
- DO NOT extract Arch openings (often marked with "A" or "AW"). Only extract actual doors (marked "D", "MD").
- DO NOT include any labels or rows that contain the word "SHOP" or "SHOP DRAWING" - these are not doors.
- Return ONLY the JSON, nothing else"""

_WINDOW_PROMPT = """This is a WINDOW SCHEDULE for a UAE villa.
Extract every row of the window schedule table.

Return ONLY this JSON:
{
  "windows": [
    {"mark":"W1","width_mm":1200,"height_mm":1500,"count":6,"type":"aluminum sliding"},
    ...
  ]
}

Rules:
- mark = window or Arch opening identifier (W1, W2, A1, A2, etc. - items starting with A are Arch openings)
- width_mm × height_mm = clear opening size in mm
- count = number of that window/arch type used in the building
- type = short description (e.g. "aluminum sliding", "casement", "arch opening")
- Include ALL rows from the schedule that are windows or Arch openings (A)
- DO NOT include any labels or rows that contain the word "SHOP" or "SHOP DRAWING" - these are not windows.
- Return ONLY the JSON, nothing else"""


def _best_pages(classification: dict, pdf_path: str, page_type: str) -> list[int]:
    pdf_cls = classification.get(pdf_path, {})
    return sorted(
        int(idx) for idx, info in pdf_cls.items() if info.get("type") == page_type
    )


def _arch_floor_pages(classification: dict, pdf_path: str) -> list[int]:
    """Return all architectural floor-plan page indices (gf, 1f, 2f, roof)."""
    pdf_cls = classification.get(pdf_path, {})
    return sorted(
        int(idx) for idx, info in pdf_cls.items()
        if info.get("type") in ("arch_gf", "arch_1f", "arch_2f", "arch_roof")
    )


def extract_openings(arch_pdf: str, classification: dict,
                     api_key: str | None = None) -> dict:
    """Run extraction + fitz cross-check."""
    out = {"doors": [], "windows": [], "totals": {}}

    # ── Doors ─────────────────────────────────────────────────────────────────
    door_pages = _best_pages(classification, arch_pdf, "door_schedule")
    if not door_pages:
        door_pages = _best_pages(classification, arch_pdf, "window_schedule")
    
    extracted_doors_raw = []
    for pi in door_pages:
        print(f"\n  [doors] reading page {pi+1}...")
        img = render_page(arch_pdf, pi, dpi=300)
        raw = ask_ai(img, _DOOR_PROMPT, api_key=api_key)
        try:
            parsed = parse_json(raw)
            items = parsed.get("doors", [])
            extracted_doors_raw.extend(items)
            print(f"    Extracted {len(items)} door types from page {pi+1}")
        except Exception as e:
            print(f"    ERROR parsing doors on page {pi+1}: {e}")
            out["doors_error"] = str(e)
            
    # Filter doors: remove any mark that starts with "W" or "A" and filter out "SHOP" hallucinations
    out["doors"] = [
        d for d in extracted_doors_raw
        if "mark" in d 
        and not str(d["mark"]).strip().upper().startswith("W")
        and not str(d["mark"]).strip().upper().startswith("A")
        and "SHOP" not in str(d["mark"]).strip().upper()
    ]
    print(f"  [doors] total filtered door types: {len(out['doors'])}")

    # ── Windows ───────────────────────────────────────────────────────────────
    win_pages = _best_pages(classification, arch_pdf, "window_schedule")
    if not win_pages:
        win_pages = _best_pages(classification, arch_pdf, "door_schedule")
        
    extracted_wins_raw = []
    for pi in win_pages:
        print(f"\n  [windows] reading page {pi+1}...")
        img = render_page(arch_pdf, pi, dpi=300)
        raw = ask_ai(img, _WINDOW_PROMPT, api_key=api_key)
        try:
            parsed = parse_json(raw)
            items = parsed.get("windows", [])
            extracted_wins_raw.extend(items)
            print(f"    Extracted {len(items)} window types from page {pi+1}")
        except Exception as e:
            print(f"    ERROR parsing windows on page {pi+1}: {e}")
            out["windows_error"] = str(e)
            
    # Filter windows: keep only marks starting with "W" or "A" and filter out "SHOP" hallucinations
    out["windows"] = [
        w for w in extracted_wins_raw
        if "mark" in w 
        and (str(w["mark"]).strip().upper().startswith("W") or str(w["mark"]).strip().upper().startswith("A"))
        and "SHOP" not in str(w["mark"]).strip().upper()
    ]
    print(f"  [windows] total filtered window types: {len(out['windows'])}")

    # ── fitz cross-check: count marks across all floor plans ──────────────────
    floor_pages = _arch_floor_pages(classification, arch_pdf)
    if floor_pages:
        import re
        from _pdf_utils import normalize_mark

        def get_equivalent_marks(mark: str) -> list[str]:
            mark_clean = mark.strip().upper()
            equiv = [mark_clean]
            
            # 1. D-1 or D1 -> AL1, AL-1, D1, D-1
            m = re.match(r"^D[-_]?(\d+)$", mark_clean)
            if m:
                num = m.group(1)
                equiv.extend([f"AL{num}", f"AL-{num}", f"D{num}", f"D-{num}"])
                
            # 2. W-1 or W1 -> W1, W-1
            m = re.match(r"^W[-_]?(\d+)$", mark_clean)
            if m:
                num = m.group(1)
                equiv.extend([f"W{num}", f"W-{num}"])
                
            # 3. A-1 or A1 -> A1, A-1, AL1, AL-1
            m = re.match(r"^A[-_]?(\d+)$", mark_clean)
            if m:
                num = m.group(1)
                equiv.extend([f"A{num}", f"A-{num}", f"AL{num}", f"AL-{num}"])
                
            return list(set(equiv))

        door_marks = [d["mark"] for d in out["doors"] if "mark" in d]
        win_marks  = [w["mark"] for w in out["windows"] if "mark" in w]
        all_marks  = door_marks + win_marks

        # Sum occurrences across all floor pages using mapped equivalents
        totals = {normalize_mark(m): 0 for m in all_marks}
        for pi in floor_pages:
            search_to_equiv = {}
            flat_search_list = []
            for m in all_marks:
                equivs = get_equivalent_marks(m)
                norm_equivs = [normalize_mark(e) for e in equivs]
                search_to_equiv[normalize_mark(m)] = norm_equivs
                flat_search_list.extend(equivs)

            try:
                c = count_token_in_page(arch_pdf, pi, flat_search_list)
            except Exception as e:
                print(f"    WARNING: Failed to count tokens on page {pi+1} ({e}). Skipping page count fallback.")
                c = {}
            for m in all_marks:
                mk = normalize_mark(m)
                equiv_counts = [c.get(eq, 0) for eq in search_to_equiv[mk]]
                totals[mk] += max(equiv_counts) if equiv_counts else 0

        print(f"\n  [fitz] Opening-mark counts across {len(floor_pages)} floor pages:")
        print("  RULE: dimensions from schedule ✔, count from floor plans ✔ (plan count is authoritative)")
        for d in out["doors"]:
            mk = normalize_mark(d.get("mark", ""))
            n  = totals.get(mk, 0)
            sched = d.get("count", "?")
            if n > 0:
                # PLAN COUNT IS AUTHORITATIVE — override schedule count
                d["count"]          = n
                d["count_source"]   = "floor_plans_fitz"
                d["count_in_plans"] = n
                if isinstance(sched, int) and abs(sched - n) >= 2:
                    print(f"      {d.get('mark')}: schedule={sched} → using plans={n} (discrepancy — plan count wins)")
                else:
                    print(f"    {d.get('mark')}: schedule={sched} → plans={n}  ✔ (plan count adopted)")
            else:
                # fitz found zero — keep schedule count but flag it
                d["count_source"] = "schedule_only"
                print(f"    {d.get('mark')}: schedule={sched}, plans=0   (mark not found on plans — keeping schedule count)")
        for w in out["windows"]:
            mk = normalize_mark(w.get("mark", ""))
            n  = totals.get(mk, 0)
            sched = w.get("count", "?")
            if n > 0:
                # PLAN COUNT IS AUTHORITATIVE — override schedule count
                w["count"]          = n
                w["count_source"]   = "floor_plans_fitz"
                w["count_in_plans"] = n
                if isinstance(sched, int) and abs(sched - n) >= 2:
                    print(f"      {w.get('mark')}: schedule={sched} → using plans={n} (discrepancy — plan count wins)")
                else:
                    print(f"    {w.get('mark')}: schedule={sched} → plans={n}  ✔ (plan count adopted)")
            else:
                w["count_source"] = "schedule_only"
                print(f"    {w.get('mark')}: schedule={sched}, plans=0   (mark not found on plans — keeping schedule count)")

    # ── Totals ────────────────────────────────────────────────────────────────
    door_count = sum(int(d.get("count") or 0) for d in out["doors"])
    win_count  = sum(int(w.get("count") or 0) for w in out["windows"])
    door_area  = sum(
        (float(d.get("width_mm") or 0) / 1000)
        * (float(d.get("height_mm") or 0) / 1000)
        * int(d.get("count") or 0)
        for d in out["doors"]
    )
    win_area   = sum(
        (float(w.get("width_mm") or 0) / 1000)
        * (float(w.get("height_mm") or 0) / 1000)
        * int(w.get("count") or 0)
        for w in out["windows"]
    )
    out["totals"] = {
        "door_count":     door_count,
        "window_count":   win_count,
        "door_area_m2":   round(door_area, 2),
        "window_area_m2": round(win_area, 2),
    }
    print(f"\n  Totals: {door_count} doors ({door_area:.1f} m²), "
          f"{win_count} windows ({win_area:.1f} m²)")
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: py _read_openings_ai.py path/to/ARCH.pdf [api_key]")
        sys.exit(1)
    arch_pdf = sys.argv[1]
    api_key  = sys.argv[2] if len(sys.argv) > 2 else None

    # Ensure classification exists
    classification = {}
    if os.path.exists(CLASS_JSON):
        with open(CLASS_JSON, encoding='utf-8') as f:
            classification = json.load(f)
    if arch_pdf not in classification:
        print(f"  ARCH PDF not classified yet — running classifier...")
        classification = classify_and_save([arch_pdf], api_key=api_key)

    data = extract_openings(arch_pdf, classification, api_key=api_key)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  Openings data saved → {OUT_JSON}")


if __name__ == "__main__":
    main()
