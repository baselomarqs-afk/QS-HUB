"""
Hybrid wall-length extractor.

Wall lengths are the single hardest dimension to extract automatically — they
require either (a) tracing the wall polylines in a vector PDF, or (b) measuring
on a raster image with a known scale.

This module provides BOTH:

    1. AI estimate via AI Vision (wall-by-wall reasoning).
       Asks AI to identify all internal partition walls on a floor plan
       and estimate each segment length using the dimension lines shown on the
       drawing. Returns a total + per-segment breakdown.

    2. Manual measurement helpers for the Streamlit UI.
       Given (page_image, scale_factor_m_per_px, list_of_clicks),
       computes the polyline length the user traced.

The Streamlit tab will:
    - show AI's AI estimate as the default value
    - let the user override by tracing on the rendered floor plan
    - persist the final value to _project_data.json

Output → _wall_data.json
{
  "gf": {
    "internal_total_m":      <number>,
    "external_total_m":      <number>,
    "ai_internal_segments":  [{"description": "...", "length_m": ...}, ...],
    "manual_internal_m":     <number or null>,
    "manual_external_m":     <number or null>,
    "source":                "ai" | "manual" | "ai+manual"
  },
  ...
}
"""
import sys, os, json, math
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from _pdf_utils import render_page, ask_ai, parse_json
from _page_classifier_ai import OUT_JSON as CLASS_JSON

OUT_JSON = os.path.join(os.path.dirname(__file__), "_wall_data.json")


# ── AI estimate prompt ────────────────────────────────────────────────────────
_WALL_PROMPT = """This is a floor plan of a UAE villa.
Your task is to estimate the total length of INTERNAL partition walls AND the total
length of EXTERNAL walls on this floor.

Read every dimension line shown on the plan. Trace each wall segment (don't double-count
where two walls meet at a corner — count each segment once).

Return ONLY this JSON:
{
  "external_walls": {
    "total_length_m": <number>,
    "segments": [
      {"description": "front facade (north)", "length_m": <number>},
      {"description": "side wall (east)",     "length_m": <number>},
      ...
    ]
  },
  "internal_walls": {
    "total_length_m": <number>,
    "segments": [
      {"description": "between living and kitchen", "length_m": <number>},
      ...
    ]
  },
  "confidence_notes": "<one sentence on how confident you are and what was unclear>"
}

Rules:
- Read dimensions in mm/cm/m as labeled — return everything in METERS
- Internal walls = partitions inside the building (between rooms)
- External walls = the outer envelope (exposed to outside or balcony)
- Each WALL SEGMENT is counted ONCE (a wall shared by 2 rooms is 1 segment, not 2)
- If you can't read a segment confidently, leave it out and note it in confidence_notes
- Return ONLY the JSON"""


def estimate_walls_ai(arch_pdf: str, page_index: int,
                       api_key: str | None = None,
                       dpi: int = 280) -> dict:
    """Ask AI to estimate internal + external wall lengths for one floor."""
    img = render_page(arch_pdf, page_index, dpi=dpi)
    raw = ask_ai(img, _WALL_PROMPT, api_key=api_key)
    try:
        return parse_json(raw)
    except Exception as e:
        return {"_error": str(e), "_raw": raw[:500]}


# ── Manual measurement helper (used by Streamlit click handler) ───────────────
def polyline_length_px(points: list[tuple[float, float]]) -> float:
    """Sum of segment lengths in pixels."""
    return sum(
        math.hypot(points[i+1][0] - points[i][0],
                   points[i+1][1] - points[i][1])
        for i in range(len(points) - 1)
    )


def pixels_to_meters(length_px: float, scale_m_per_px: float) -> float:
    """Convert pixel length to meters given the drawing scale."""
    return round(length_px * scale_m_per_px, 2)


def compute_scale_from_known_dim(known_dim_m: float, click_a: tuple, click_b: tuple) -> float:
    """
    Calibrate the drawing scale:
    user clicks two points on a dimension line whose value is known_dim_m (in meters),
    and we compute m/px.
    """
    px = math.hypot(click_b[0] - click_a[0], click_b[1] - click_a[1])
    if px <= 0:
        return 0.0
    return known_dim_m / px


# ── Per-floor orchestration ───────────────────────────────────────────────────
def extract_walls_all_floors(arch_pdf: str, classification: dict,
                              api_key: str | None = None,
                              floor_areas: dict[str, float] | None = None) -> dict:
    """
    Run AI estimation for every architectural floor plan.

    Args:
        floor_areas: optional {"gf": 330, "1f": 290, ...} from ARCH extractor —
                     used for sanity checks [W7].
    """
    out       = {}
    pdf_cls   = classification.get(arch_pdf, {})
    floor_map = {"arch_gf": "gf", "arch_1f": "1f", "arch_2f": "2f", "arch_roof": "roof"}
    floor_areas = floor_areas or {}

    for idx_str, info in pdf_cls.items():
        ptype = info.get("type")
        if ptype not in floor_map:
            continue
        floor_key = floor_map[ptype]
        if floor_key == "roof":
            continue   # roof has no internal walls
        pi   = int(idx_str)
        print(f"\n  [walls·{floor_key}] page {pi+1}...")
        ai   = estimate_walls_ai(arch_pdf, pi, api_key=api_key)
        ext  = (ai.get("external_walls", {}) or {}).get("total_length_m")
        intl = (ai.get("internal_walls", {}) or {}).get("total_length_m")

        rec  = {
            "internal_total_m":     intl,
            "external_total_m":     ext,
            "ai_internal_segments": (ai.get("internal_walls", {}) or {}).get("segments", []),
            "ai_external_segments": (ai.get("external_walls", {}) or {}).get("segments", []),
            "ai_notes":             ai.get("confidence_notes", ""),
            "manual_internal_m":    None,
            "manual_external_m":    None,
            "source":               "ai",
            "warnings":             [],
        }

        # ── Sanity check vs floor area [W7] ───────────────────────────────────
        fa = floor_areas.get(floor_key)
        if fa and intl is not None:
            ratio = intl / fa
            if ratio < 0.3:
                rec["warnings"].append(
                    f"internal_walls/floor_area = {ratio:.2f} m/m² (very low; "
                    f"typical is 0.5-2.0) — AI may have missed segments"
                )
            elif ratio > 5.0:
                rec["warnings"].append(
                    f"internal_walls/floor_area = {ratio:.2f} m/m² (very high; "
                    f"typical is 0.5-2.0) — AI may have double-counted"
                )
        if fa and ext is not None:
            # External perimeter should be roughly proportional to sqrt(area) × 4
            expected_perim = 4 * (fa ** 0.5)
            if ext < 0.5 * expected_perim or ext > 2.5 * expected_perim:
                rec["warnings"].append(
                    f"external_walls = {ext} m vs ~4×sqrt(area) ≈ {expected_perim:.1f} m "
                    f"— verify"
                )

        out[floor_key] = rec
        print(f"    internal: {intl} m, external: {ext} m"
              + (f" [⚠ {len(rec['warnings'])} warnings]" if rec['warnings'] else ""))
    return out


def apply_manual_override(wall_data: dict, floor_key: str,
                          manual_internal_m: float | None = None,
                          manual_external_m: float | None = None) -> dict:
    """Called by the UI when user provides a measured value."""
    f = wall_data.setdefault(floor_key, {})
    if manual_internal_m is not None:
        f["manual_internal_m"] = manual_internal_m
        f["internal_total_m"]  = manual_internal_m
    if manual_external_m is not None:
        f["manual_external_m"] = manual_external_m
        f["external_total_m"]  = manual_external_m
    if manual_internal_m is not None or manual_external_m is not None:
        f["source"] = "ai+manual" if f.get("source") == "ai" else "manual"
    return wall_data


def main():
    if len(sys.argv) < 2:
        print("Usage: py _wall_length_extractor.py path/to/ARCH.pdf [api_key]")
        sys.exit(1)
    arch_pdf = sys.argv[1]
    api_key  = sys.argv[2] if len(sys.argv) > 2 else None

    classification = {}
    if os.path.exists(CLASS_JSON):
        with open(CLASS_JSON, encoding='utf-8') as f:
            classification = json.load(f)
    if arch_pdf not in classification:
        from _page_classifier_ai import classify_and_save
        classification = classify_and_save([arch_pdf], api_key=api_key)

    data = extract_walls_all_floors(arch_pdf, classification, api_key=api_key)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  Wall data saved → {OUT_JSON}")


if __name__ == "__main__":
    main()
