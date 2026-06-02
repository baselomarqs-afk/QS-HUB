"""
Bridge: _project_data.json  →  engine.item_calculator inputs.

The engine's `calculate_item(item_key, inputs)` expects a flat dict with keys
like `longest_length`, `gf_area`, `foundations_schedule`, `beams_schedule`,
`tb_width`, `tb_total_length`, `is_ground_floor`, etc.

This module reads `_project_data.json` (the single source of truth produced
by `_master_extractor.py` + reviewed in the Streamlit Schedule Review tab),
unpacks the nested structure, and returns:

    base   : dict with project-wide values
    floors : { "gf": {...floor-specific overrides...},
               "1f": {...},
               "roof": {...} }

Usage pattern (replaces the hardcoded base/FLOORS in _live_test_ai.py):

    from _project_to_engine import load_engine_inputs, C, CF
    base, floors = load_engine_inputs()
    foundation_concrete = C("foundation_concrete", base)
    sog_vol             = CF("slab_on_grade", floors["gf"], base)
"""
import os, json, statistics
from typing import Optional

from _qto_config import PROJECT_JSON, get_logger
from engine.item_calculator import calculate_item

log = get_logger("project_to_engine")


# ── Loader ────────────────────────────────────────────────────────────────────
def load_project_data(path: str = PROJECT_JSON) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No project data at {path}.\n"
            "Run `py _master_extractor.py --str ... --arch ...` first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def require_approved(project: dict):
    """Raise if user hasn't ticked the 'approve' checkbox in Schedule Review."""
    if not project.get("_approved"):
        raise PermissionError(
            "Project data is not approved yet. "
            "Open the Streamlit app → Schedule Review tab → review and approve."
        )


# ── Build engine inputs ───────────────────────────────────────────────────────
def _foundations_schedule(project: dict) -> list[dict]:
    """Convert footings schedule → engine format with meter units."""
    foots = (project.get("schedules", {})
                     .get("foundation", {})
                     .get("footings", []))
    out = []
    for f in foots:
        out.append({
            "type":      f.get("type"),
            "long_m":    (f.get("long_mm")  or 0) / 1000,
            "short_m":   (f.get("short_mm") or 0) / 1000,
            "depth_m":   (f.get("depth_mm") or 0) / 1000,
            "count":     f.get("count", 0) or 0,
        })
    return out


def _neck_columns_schedule(project: dict) -> list[dict]:
    """Approximate neck columns from foundations × 0.5m typical neck height."""
    foots = _foundations_schedule(project)
    out = []
    for f in foots:
        out.append({
            "width_m":  f["short_m"],
            "depth_m":  f["long_m"],
            "height_m": 0.5,
            "count":    f["count"],
        })
    return out


def _tb_weighted_dims(project: dict) -> tuple[float, float, float]:
    """
    Returns (width_m, depth_m, total_length_m) — count-weighted average for the
    'tb_width'/'tb_depth' single-value engine parameters.
    """
    tbs = (project.get("schedules", {})
                  .get("tie_beam", {})
                  .get("tie_beams", []))
    if not tbs:
        return 0.2, 0.6, 0.0
    # We don't have per-mark segment counts here unless schedule_data carried them;
    # fall back to plain mean if no count info found
    widths  = [(t.get("width_mm") or 0)/1000 for t in tbs]
    depths  = [(t.get("depth_mm") or 0)/1000 for t in tbs]
    counts  = [t.get("count_segments") or 1 for t in tbs]
    total_c = sum(counts) or 1
    w_avg   = sum(w*c for w, c in zip(widths, counts)) / total_c
    d_avg   = sum(d*c for d, c in zip(depths, counts)) / total_c
    # total length is in project["tb_total_length"] if reviewer entered it; else 0
    total_len = project.get("tb_total_length", 0.0) or 0.0
    return round(w_avg, 4), round(d_avg, 4), float(total_len)


def _slab_beams(project: dict, slab_key: str) -> list[dict]:
    """Convert slab beams schedule to engine format (meters)."""
    beams = (project.get("schedules", {})
                    .get(slab_key, {})
                    .get("beams", []))
    out = []
    for b in beams:
        out.append({
            "mark":     b.get("mark"),
            "width_m":  (b.get("width_mm") or 0) / 1000,
            "depth_m":  (b.get("depth_mm") or 0) / 1000,
            "length_m": b.get("length_m") or 0.0,
            "count":    b.get("count", 0) or 0,
        })
    return out


def _column_volume_for_floor(project: dict, floor_key: str) -> float:
    """Sum column concrete volume for a specific floor from column schedule."""
    cols = (project.get("schedules", {})
                   .get("column_schedule", {})
                   .get("columns", []))
    total = 0.0
    for c in cols:
        w = (c.get("width_mm") or 0) / 1000
        d = (c.get("depth_mm") or 0) / 1000
        h = (c.get(f"height_{floor_key}_mm") or 0) / 1000
        n = c.get(f"count_{floor_key}") or 0
        total += w * d * h * n
    return round(total, 3)


def load_engine_inputs(path: str = PROJECT_JSON,
                       require_approval: bool = False) -> tuple[dict, dict]:
    """
    Load _project_data.json and return (base, floors).

    Args:
        require_approval: If True, raises PermissionError when _approved=False.
    """
    project = load_project_data(path)
    if require_approval:
        require_approved(project)

    tb_w, tb_d, tb_len = _tb_weighted_dims(project)
    base = {
        # Project metadata
        "villa_type":            project.get("villa_type"),
        "structural_levels":     project.get("structural_levels"),
        # Plan dimensions
        "longest_length":        project.get("longest_length") or 0.0,
        "longest_width":         project.get("longest_width")  or 0.0,
        "gf_area":               project.get("gf_area")        or 0.0,
        "external_perimeter":    project.get("external_perimeter") or 0.0,
        "ext_perimeter":         project.get("ext_perimeter")  or project.get("external_perimeter") or 0.0,
        "plot_area":             project.get("plot_area")      or 0.0,
        "compound_length":       project.get("compound_length") or 0.0,
        "roof_perimeter":        project.get("roof_perimeter") or 0.0,
        "roof_slab_area":        project.get("roof_slab_area") or 0.0,
        "total_villa_height":    project.get("total_villa_height") or 0.0,
        "parapet_height":        project.get("parapet_height") or 1.0,
        "excavation_depth":      project.get("excavation_depth") or 1.25,
        # Schedules (already in engine-ready format)
        "foundations_schedule":  _foundations_schedule(project),
        "neck_columns_schedule": _neck_columns_schedule(project),
        # Tie beam aggregates
        "tb_width":              tb_w,
        "tb_depth":              tb_d,
        "tb_total_length":       tb_len,
        # Openings
        "door_count":            project.get("openings", {}).get("totals", {}).get("door_count", 0),
        "window_area_m2":        project.get("openings", {}).get("totals", {}).get("window_area_m2", 0),
    }

    # Per-floor blocks
    floors = {}
    proj_floors = project.get("floors", {})
    walls       = project.get("walls", {})

    for fk in ("gf", "1f", "2f", "roof"):
        if fk not in proj_floors:
            continue
        f = proj_floors[fk]
        w = walls.get(fk, {})
        slab_key = {
            "gf":   None,         # SOG instead
            "1f":   "slab_1f",
            "2f":   "slab_2f",
            "roof": "slab_roof",
        }[fk]
        floors[fk] = {
            "floor_id":         fk,
            "is_ground_floor":  bool(f.get("is_ground_floor", fk == "gf")),
            "floor_area":       f.get("area") or 0.0,
            "ext_perimeter":    f.get("ext_perimeter") or base["ext_perimeter"],
            "external_perimeter": f.get("ext_perimeter") or base["external_perimeter"],
            "wall_internal":    w.get("internal_total_m") or 0.0,
            "wall_external":    w.get("external_total_m") or 0.0,
            "wet_area":         f.get("wet_area") or 0.0,
            "wet_perimeter":    f.get("wet_perimeter") or 0.0,
            "dry_area":         f.get("dry_area") or 0.0,
            "balcony_area":     f.get("balcony_area") or 0.0,
            "column_volume":    _column_volume_for_floor(project, fk),
            "beams_schedule":   _slab_beams(project, slab_key) if slab_key else [],
            "slab_thickness_m": (project.get("schedules", {})
                                          .get(slab_key, {})
                                          .get("slab_thickness_mm") or 0) / 1000 if slab_key else 0.0,
        }

    return base, floors


# ── Convenience wrappers used in test scripts ─────────────────────────────────
def C(item_key: str, base: dict) -> Optional[float]:
    """Compute an item against project-wide base."""
    return calculate_item(item_key, base)


def CF(item_key: str, floor: dict, base: dict) -> Optional[float]:
    """Compute an item against base + floor overrides."""
    return calculate_item(item_key, {**base, **floor})


# ── CLI: print engine inputs for inspection ───────────────────────────────────
if __name__ == "__main__":
    import argparse, pprint
    ap = argparse.ArgumentParser()
    ap.add_argument("--path",     default=PROJECT_JSON)
    ap.add_argument("--require-approval", action="store_true")
    args = ap.parse_args()
    try:
        base, floors = load_engine_inputs(args.path, require_approval=args.require_approval)
        print("\n── BASE ──")
        pprint.pprint(base, sort_dicts=False)
        print("\n── FLOORS ──")
        pprint.pprint(floors, sort_dicts=False)
    except (FileNotFoundError, PermissionError) as e:
        print(f"ERROR: {e}")
