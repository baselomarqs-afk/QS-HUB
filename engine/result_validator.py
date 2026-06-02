"""
Validates AI-calculated quantities against reference ranges
built from real UAE villa BOQ files.
"""
import json
import os
import statistics

_DB_PATH      = os.path.join(os.path.dirname(__file__), "reference_ranges.json")
_PROJECT_JSON = os.path.join(os.path.dirname(__file__), "..", "_project_data.json")


def _load_db() -> dict:
    try:
        with open(_DB_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def reload_db() -> dict:
    """Force reload reference DB from disk (used after _build_reference_db.py --add)."""
    global _DB
    _DB = _load_db()
    return _DB


_DB: dict = _load_db()


def auto_villa_type() -> str | None:
    """
    Auto-detect villa_type from _project_data.json [W8].
    Returns 'G', 'G+1', 'G+2', etc., or None if project data unavailable.
    """
    try:
        with open(_PROJECT_JSON, encoding="utf-8") as f:
            project = json.load(f)
    except Exception:
        return None
    levels = project.get("structural_levels")
    if levels is None:
        return None
    if levels <= 2:
        return "G"
    return f"G+{levels - 2}"


# ── Key aliases: our item keys → reference DB keys ────────────────────────────
_ALIAS: dict[str, str] = {
    # ── Sub-structure (exact matches) ────────────────────────────────────────
    "excavation":            "excavation",
    "foundation_pcc":        "foundation_pcc",
    "foundation_concrete":   "foundation_concrete",
    "neck_column_concrete":  "neck_column_concrete",
    "road_base":             "road_base",
    "backfill":              "backfill",
    # polyethylene_found alone = ~134 m² (just foundation level)
    # reference "polyethylene" = both levels combined (~450 m²) → use poly_sheet_combined
    # "polyethylene_found":  [skip individual — use poly_sheet_combined for combined check]
    "slab_on_grade":         "slab_on_grade",

    # ── Tie beams ────────────────────────────────────────────────────────────
    "tie_beam_concrete":     "tie_beam_concrete",
    # tie_beam_pcc alone is ~5 m³; reference "foundation_pcc" = combined footing+TB PCC (22 m³)
    # Individual comparison gives misleading 🟡 — validate via pcc_combined instead
    # "tie_beam_pcc":        [skip individual — use pcc_combined]
    # virtual key (foundation_pcc + tie_beam_pcc summed) — correct combined comparison
    "pcc_combined":          "foundation_pcc",

    # ── Bitumen items — no unit-matched reference available ──────────────────
    # (BOQ references are in m³ concrete; bitumen is in m²; do NOT compare)
    # "foundation_bitumen":  [no ref — m² vs m³ would be meaningless]
    # "neck_column_bitumen": [no ref]
    # "tie_beam_bitumen":    [no ref]

    # ── Poly sheet / anti-termite ────────────────────────────────────────────
    # poly_sheet_tb (414 m²) + polyethylene_found (134 m²) = ~548 m² combined
    # reference "polyethylene" = combined both levels (median 450 m²)
    # poly_sheet_tb alone comparing to full reference is misleading — use combined instead
    # "poly_sheet_tb":       [skip individual — too high alone vs combined reference]
    "poly_sheet_combined":   "polyethylene",   # virtual key for combined poly sheet

    # ── Columns ──────────────────────────────────────────────────────────────
    "col_gf_to_1st":         "column_concrete",
    "col_1st_to_2nd":        "column_concrete",
    "col_roof":              "column_concrete",

    # ── Beams & slabs (now backed by 11 real villa BOQs) ─────────────────────
    "beam_concrete_1st":     "beam_concrete",
    "beam_concrete_2nd":     "beam_concrete",
    "beam_concrete_roof":    "beam_concrete",
    "slab_concrete_1st":     "slab_concrete",
    "slab_concrete_2nd":     "slab_concrete",
    "slab_concrete_roof":    "slab_concrete",
    "staircase_1st":         "staircase_concrete",

    # ── Parapet ──────────────────────────────────────────────────────────────
    # parapet_block_work is in m²; reference "parapet" is parapet CONCRETE in m³ — unit mismatch
    # "parapet_block_work": [no ref]
    "parapet_concrete":      "parapet",

    # ── Block work ───────────────────────────────────────────────────────────
    # solid_block_work = perimeter tie beam formwork only (~73 m²)
    # reference "solid_block" = all solid block throughout building (~208 m² median)
    # Comparing partial to total gives false 🟡 — skip
    # "solid_block_work":    [skip — perimeter-only vs full-building reference]
    "internal_block_gf":     "internal_block",
    "internal_block_1f":     "internal_block",
    "internal_block_2f":     "internal_block",
    # thermal_block now n=3 — still small but better than nothing
    "thermal_block_gf":      "thermal_block",
    "thermal_block_1f":      "thermal_block",

    # ── Finishes (now backed by 7-13 real villa BOQs) ────────────────────────
    "skirting_gf":           "skirting",
    "internal_plaster":      "internal_plaster",
    "internal_plaster_gf":   "internal_plaster",
    "internal_plaster_1f":   "internal_plaster",
    "external_plaster":      "external_plaster",
    "ceiling_plaster":       "ceiling_plaster",
    "internal_paint":        "internal_paint",
    "external_paint":        "external_paint",

    # ── Waterproofing (now have references) ──────────────────────────────────
    "foundation_bitumen":    "foundation_bitumen",
    # neck_column_bitumen / tie_beam_bitumen are small-area items (tens of m²);
    # comparing them to foundation_bitumen's range (hundreds of m²) produced
    # false 🔴 outliers. No magnitude-matched reference → leave unmapped.
    # "neck_column_bitumen": [no comparable reference]
    # "tie_beam_bitumen":    [no comparable reference]
    "wet_waterproofing":     "wet_waterproofing",
    "wet_wp_gf":             "wet_waterproofing",
    "wet_wp_1f":             "wet_waterproofing",
    "wet_wp_2f":             "wet_waterproofing",

    # ── External ─────────────────────────────────────────────────────────────
    "interlock_paving":      "interlock_paving",
    "compound_wall":         "compound_wall",
    "roof_waterproofing":    "polyethylene",

    # ── Openings ─────────────────────────────────────────────────────────────
    "door_openings":         "door_openings",
    "window_openings":       "window_openings",
}


def validate_quantity(item_key: str, quantity: float,
                      villa_type: str | None = None) -> dict:
    """
    Returns a validation dict:
      status:  'ok' | 'low' | 'high' | 'outlier' | 'no_data'
      label:   human-readable label with emoji
      ref:     reference dict (min/max/median/count) or None
      pct_dev: % deviation from median

    Args:
        item_key:   The item key in our engine's output.
        quantity:   The computed quantity to validate.
        villa_type: Optional UAE villa type (e.g. "G+1", "G+2"). When provided,
                    the validator picks the narrower by_villa_type band if it has
                    >= 2 samples for that type — giving more accurate comparisons
                    for non-typical villas.
    """
    ref_key = _ALIAS.get(item_key)
    if not ref_key or ref_key not in _DB:
        return {"status": "no_data", "label": "⚪ No reference", "ref": None, "pct_dev": None}

    # Auto-detect villa type if caller didn't specify [W8]
    if villa_type is None:
        villa_type = auto_villa_type()

    ref  = _DB[ref_key]
    # Prefer same-type band if available
    if villa_type and ref.get("by_villa_type"):
        sub = ref["by_villa_type"].get(villa_type)
        if sub and sub.get("count", 0) >= 2:
            ref = {
                **ref,
                "min":    sub["min"],
                "max":    sub["max"],
                "median": sub["median"],
                "count":  sub["count"],
                "_filtered_by": villa_type,
            }
    vmin = ref["min"]
    vmax = ref["max"]
    med  = ref["median"]
    std  = ref.get("stdev", 0)

    pct_dev = round(abs(quantity - med) / med * 100, 1) if med > 0 else None

    # Define "normal" band: median ± 1.5 × stdev, but at minimum within [min, max]
    low_ok  = max(vmin, med - 1.5 * std) if std > 0 else vmin
    high_ok = min(vmax, med + 1.5 * std) if std > 0 else vmax

    if quantity < vmin * 0.5:
        status = "outlier"
        label  = f"🔴 Very low (ref min {vmin:.0f})"
    elif quantity > vmax * 1.5:
        status = "outlier"
        label  = f"🔴 Very high (ref max {vmax:.0f})"
    elif quantity < low_ok:
        status = "low"
        label  = f"🟡 Below typical (median {med:.0f})"
    elif quantity > high_ok:
        status = "high"
        label  = f"🟡 Above typical (median {med:.0f})"
    else:
        status = "ok"
        label  = f"🟢 Normal (median {med:.0f})"

    return {
        "status":  status,
        "label":   label,
        "ref":     ref,
        "pct_dev": pct_dev,
    }


def validate_all_results(results: dict[str, float],
                          villa_type: str | None = None) -> dict[str, dict]:
    """
    Validates a dict of {item_key: quantity}.
    Returns {item_key: validation_dict}.
    """
    return {
        k: validate_quantity(k, v, villa_type=villa_type)
        for k, v in results.items() if v is not None
    }


def get_reference_summary() -> list[dict]:
    """Returns a flat list of all reference ranges for display."""
    rows = []
    for key, data in _DB.items():
        if key.startswith("_") or not isinstance(data, dict) or "min" not in data:
            continue   # skip metadata blocks like _projects
        rows.append({
            "Item":        key.replace("_", " ").title(),
            "Projects":    data["count"],
            "Min":         data["min"],
            "Median":      data["median"],
            "Max":         data["max"],
            "Unit":        data["unit"].upper(),
            "Std Dev":     data.get("stdev", 0),
        })
    return sorted(rows, key=lambda r: r["Item"])


def list_known_villa_types() -> list[str]:
    """Return the distinct villa_type values present in the DB metadata."""
    projs = _DB.get("_projects", {})
    types = set()
    for _, meta in projs.items():
        vt = meta.get("villa_type")
        if vt and vt != "unknown":
            types.add(vt)
    return sorted(types)
