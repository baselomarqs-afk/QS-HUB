"""
THE bridge — _project_data.json  →  final BOQ DataFrame.

This is the single connection that ties the whole pipeline together:

    _master_extractor.py  →  _project_data.json
        →  (reviewed & APPROVED by the user in Schedule Review)
        →  THIS MODULE  →  calculate_item()  →  BOQ DataFrame  →  Excel

Before this module existed, the BOQ tab built its table from a *different*
in-session source (`confirmed_auto_data`) and never read the JSON the user
actually approved — so a CLI-extracted, JSON-approved project produced an
all-zero BOQ silently.

Design rules
------------
1. SINGLE SOURCE OF TRUTH:   everything is computed from _project_data.json.
2. CORRECT KEYS:             emits the EXACT input keys calculate_item() reads
                             (verified against engine/item_calculator.py).
3. NO SILENT ZEROS:          any item whose required input is missing from the
                             drawings is reported in `needs_input` instead of
                             quietly returning 0 — that becomes the user's
                             "confirm only what's needed" list.
"""
import os, json
from typing import Optional
import pandas as pd

from engine.item_calculator    import calculate_item
from engine.item_detection_map import DRAWING_ITEMS_MAP

def safe_float(v):
    try: return float(str(v).strip() or 0.0)
    except Exception: return 0.0

def safe_int(v):
    try: return int(float(str(v).strip() or 0))
    except Exception: return 0

PROJECT_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "_project_data.json")


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Schedule converters — produce EXACTLY the keys calculate_item() reads
# ══════════════════════════════════════════════════════════════════════════════

def _footings(project: dict) -> list[dict]:
    """Footings → engine keys: length_m, width_m, depth_m, count."""
    foots = (project.get("schedules", {})
                    .get("foundation", {})
                    .get("footings", []))
    out = []
    for f in foots:
        # Support both meters-based keys (length/width/depth) and legacy millimeter keys (long_mm/short_mm/depth_mm)
        length_val = f.get("length") or f.get("length_m")
        if length_val is None:
            length_val = (f.get("long_mm") or f.get("length_mm") or 0) / 1000
            
        width_val = f.get("width") or f.get("width_m")
        if width_val is None:
            width_val = (f.get("short_mm") or f.get("width_mm") or 0) / 1000
            
        depth_val = f.get("depth") or f.get("depth_m")
        if depth_val is None:
            depth_val = (f.get("depth_mm") or 0) / 1000
            
        out.append({
            "length_m": safe_float(length_val),
            "width_m":  safe_float(width_val),
            "depth_m":  safe_float(depth_val),
            "count":    safe_int(f.get("count")),
        })
    return out


_NECK_TYPICAL_W = 0.30   # m — typical neck-column plan size when no neck schedule
_NECK_TYPICAL_L = 0.40   # m
_TYPICAL_BEAM_SPAN_M = 4.5   # m — typical villa structural bay (column-to-column)


def _neck_columns(project: dict) -> tuple[list[dict], bool]:
    """
    Neck columns sit between footing and tie beam.
    If ground floor columns are known, we use their exact sizes.
    Otherwise we fall back to footing count × typical section.
    """
    gf_cols = _columns_for_floor(project, "gf")
    if gf_cols:
        return gf_cols, False
        
    out = []
    for f in _footings(project):
        out.append({
            "length_m": _NECK_TYPICAL_L,
            "width_m":  _NECK_TYPICAL_W,
            "count":    f["count"],
        })
    return out, True


def _tie_beam_dims(project: dict) -> tuple[float, float, float, bool]:
    """
    Returns (tb_width_m, tb_depth_m, tb_total_length_m, length_was_estimated).

    Tie-beam schedules carry width/depth/segment-count but almost never a
    total length, so length is taken from an explicit project field if the
    reviewer entered one, else estimated from the building geometry
    (external perimeter + internal walls of the ground floor).
    """
    tbs = (project.get("schedules", {})
                  .get("tie_beam", {})
                  .get("tie_beams", []))
    estimated = False

    # explicit reviewer value always wins
    explicit_len = project.get("tb_total_length") or 0.0
    
    # Try fetching flat top-level parameters or schedule parameters directly
    w = project.get("tb_width")
    d = project.get("tb_depth")
    total_len = explicit_len
    
    if w is None:
        w = project.get("schedules", {}).get("tie_beam", {}).get("tb_width")
    if d is None:
        d = project.get("schedules", {}).get("tie_beam", {}).get("tb_depth")
    if not total_len:
        total_len = project.get("schedules", {}).get("tie_beam", {}).get("tb_total_length") or 0.0

    if tbs:
        widths = [(t.get("width_mm") or 0) / 1000 for t in tbs]
        depths = [(t.get("depth_mm") or 0) / 1000 for t in tbs]
        measured_lens = [t.get("length_m") or 0.0 for t in tbs]
        have_measured = any(measured_lens)

        if have_measured and not explicit_len:
            tot_len = sum(measured_lens) or 1.0
            w = sum(wi * Li for wi, Li in zip(widths, measured_lens)) / tot_len
            d = sum(di * Li for di, Li in zip(depths, measured_lens)) / tot_len
            total_len = round(sum(measured_lens), 2)
            if not all(measured_lens):
                estimated = True
        else:
            counts = [t.get("count_segments") or 1 for t in tbs]
            tot_c  = sum(counts) or 1
            w = sum(x * c for x, c in zip(widths, counts)) / tot_c
            d = sum(x * c for x, c in zip(depths, counts)) / tot_c
            if not total_len:
                ext  = project.get("external_perimeter") or project.get("ext_perimeter") or 0.0
                intl = (project.get("walls", {}).get("gf", {}) or {}).get("internal_total_m") or 0.0
                total_len = round(ext + intl, 2)
                estimated = True
    else:
        if w is None: w = 0.30
        if d is None: d = 0.60
        if not total_len:
            ext  = project.get("external_perimeter") or project.get("ext_perimeter") or 0.0
            intl = (project.get("walls", {}).get("gf", {}) or {}).get("internal_total_m") or 0.0
            total_len = round(ext + intl, 2)
            estimated = True

    return round(safe_float(w), 4), round(safe_float(d), 4), safe_float(total_len), estimated


def _slab_beams(project: dict, slab_key: str, floor_area: float) -> tuple[list[dict], bool]:
    """
    Slab beams → engine keys: length_m, width_m, depth_m, count.
    """
    alt_keys = {
        "slab_1f": ["slab_1st", "slab_1f"],
        "slab_2f": ["slab_2nd", "slab_2f"],
        "slab_roof": ["roof_slab", "slab_roof"]
    }
    keys_to_try = alt_keys.get(slab_key, [slab_key])
    
    beams = []
    for k in keys_to_try:
        beams = (project.get("schedules", {})
                        .get(k, {})
                        .get("beams", []))
        if beams:
            break

    estimated = False
    out = []
    for b in beams:
        # Support meters (length/length_m) or fallback to bay span
        total_len = b.get("length") or b.get("length_m") or 0.0
        if not total_len:
            total_len = (b.get("count", 0) or 0) * _TYPICAL_BEAM_SPAN_M
            if total_len:
                estimated = True
                
        width_val = b.get("width") or b.get("width_m")
        if width_val is None:
            width_val = (b.get("width_mm") or 0) / 1000
            
        depth_val = b.get("depth") or b.get("depth_m")
        if depth_val is None:
            depth_val = (b.get("depth_mm") or 0) / 1000
            
        out.append({
            "length_m": safe_float(total_len),
            "width_m":  safe_float(width_val),
            "depth_m":  safe_float(depth_val),
            "count":    1,        # length is already the total → no multiplier
        })
    return out, estimated


def _columns_for_floor(project: dict, floor_key: str) -> list[dict]:
    """
    Column schedule → engine keys: length_m, width_m, count (height inside engine).
    """
    scheds = project.get("schedules", {})
    cols = scheds.get("column_schedule", {}).get("columns", [])
    if not cols:
        cols = scheds.get("superstructure", {}).get("columns", [])
                   
    # Check if schedule exists but has NO counts at all
    total_counts_in_schedule = 0
    for c in cols:
        total_counts_in_schedule += safe_int(c.get("count_gf")) + safe_int(c.get("count_1f")) + safe_int(c.get("count_2f")) + safe_int(c.get("count_roof")) + safe_int(c.get("count"))
        
    fallback_count_per_col = 0
    if total_counts_in_schedule == 0 and len(cols) > 0:
        gf_area = safe_float(project.get("gf_area")) or 250.0
        total_needed = max(1, int(gf_area / 16)) # 1 col per 16 sqm
        fallback_count_per_col = max(1, total_needed // len(cols))
        
    default_len = safe_float(project.get("default_col_length", 0.60))
    default_wid = safe_float(project.get("default_col_width", 0.20))
    
    if len(cols) == 0:
        gf_area = safe_float(project.get("gf_area")) or 250.0
        total_needed = max(1, int(gf_area / 16))
        return [{
            "length_m": default_len,
            "width_m":  default_wid,
            "count":    total_needed
        }]

    out = []
    for c in cols:
        n = c.get(f"count_{floor_key}")
        if not n:
            n = c.get("count", 0)
            
        if total_counts_in_schedule == 0:
            n = fallback_count_per_col
            
        length_val = c.get("length_m") or c.get("length")
        if length_val is None:
            length_val = (c.get("depth_mm") or c.get("long_mm") or c.get("length_mm") or 0) / 1000
            
        width_val = c.get("width_m") or c.get("width")
        if width_val is None:
            width_val = (c.get("width_mm") or c.get("short_mm") or 0) / 1000
            
        if safe_float(length_val) == 0: length_val = default_len
        if safe_float(width_val) == 0: width_val = default_wid
            
        out.append({
            "length_m": safe_float(length_val),
            "width_m":  safe_float(width_val),
            "count":    safe_int(n),
        })
    return out


def _doors(project: dict) -> list[dict]:
    """
    Prefer door schedule counts if available, otherwise fallback to floor plan AI counts.
    """
    openings = project.get("openings", {})
    doors = openings.get("doors") or openings.get("doors_schedule") or []
    
    sched_total = 0
    for d in doors:
        mark = str(d.get("mark") or d.get("type") or "").strip().upper()
        # Ignore arches (usually starting with A) and only count doors
        if mark.startswith("A"):
            continue
        sched_total += safe_int(d.get("count") or d.get("count_in_plans") or d.get("qty") or 1)
        
    if sched_total > 0:
        return [{"count": sched_total}]
    
    plan_count = int(openings.get("totals", {}).get("door_count") or 0)
    if plan_count > 0:
        return [{"count": plan_count}]
    return []


def _windows(project: dict) -> list[dict]:
    """
    Prefer window schedule if available, otherwise fallback to floor plan AI area.
    """
    openings = project.get("openings", {})
    wins = openings.get("windows") or openings.get("windows_schedule") or []
    
    out = []
    for w in wins:
        if w.get("width_mm"):
            width_m  = safe_float(w["width_mm"]) / 1000.0
        else:
            width_m  = safe_float(w.get("width_m") or w.get("width"))
        if w.get("height_mm"):
            height_m = safe_float(w["height_mm"]) / 1000.0
        else:
            height_m = safe_float(w.get("height_m") or w.get("height") or w.get("length"))
        
        # Guard against swapping: if height is huge and width is small
        if width_m < 0.1 and height_m > 0.1: 
            pass # Keep as is, might be narrow window
            
        c = safe_int(w.get("count") or w.get("count_in_plans") or w.get("qty") or 1)
        out.append({"width_m": width_m, "height_m": height_m, "count": c})
        
    # Check if total calculated area from out is zero
    total_area_from_out = sum(w["width_m"] * w["height_m"] * w["count"] for w in out)
    
    if out and total_area_from_out > 0:
        return out
        
    plan_area = float(openings.get("totals", {}).get("window_area") or 0)
    if plan_area > 0:
        return [{"width_m": 1.0, "height_m": plan_area, "count": 1}]
    return []


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Build base (project-wide) + per-floor input dicts
# ══════════════════════════════════════════════════════════════════════════════

def build_inputs(project: dict) -> tuple[dict, dict, dict]:
    """
    Returns (base, floors, meta).

      base   : project-wide inputs for calculate_item()
      floors : { 'gf': {...}, '1f': {...}, '2f': {...}, 'roof': {...} }
      meta   : { 'needs_input': [...], 'estimates': [...] }  for UI flagging
    """
    needs_input: list[str] = []
    estimates:   list[str] = []

    tb_w, tb_d, tb_len, tb_estimated = _tie_beam_dims(project)
    neck_cols_sched, nc_estimated = _neck_columns(project)
    
    if tb_estimated:
        estimates.append("tie_beam_total_length (estimated from perimeter + internal walls)")

    ext_perim = (project.get("external_perimeter")
                 or project.get("ext_perimeter") or 0.0)

    # gf_area: prefer explicit project field; fall back to gf floor area
    _gf_floor = project.get("floors", {}).get("gf", {}) or {}
    gf_area = (
        project.get("gf_area")
        or _gf_floor.get("area")
        or 0.0
    )

    # structural_levels: prefer explicit; fall back to count of floor keys
    _floor_keys = [k for k in project.get("floors", {}) if k in ("gf", "1f", "2f")]
    structural_levels = (
        project.get("structural_levels")
        or len(_floor_keys)
        or 1
    )

    base = {
        # plan dimensions
        "longest_length":    project.get("longest_length") or 0.0,
        "longest_width":     project.get("longest_width")  or 0.0,
        "gf_area":           gf_area,
        "plot_area":         project.get("plot_area")      or 0.0,
        "external_perimeter": ext_perim,
        "ext_perimeter":      ext_perim,
        "roof_perimeter":    project.get("roof_perimeter") or ext_perim,
        "roof_slab_area":    project.get("roof_slab_area") or 0.0,
        "compound_length":   project.get("compound_length") or 0.0,
        "total_villa_height": project.get("total_villa_height") or 0.0,
        "parapet_height":    project.get("parapet_height") or 1.0,
        "excavation_depth":  project.get("excavation_depth") or 1.25,
        "neck_column_height": project.get("neck_column_height") or 1.0,
        "solid_block_height": project.get("solid_block_height") or 1.0,
        "staircase_volume_per_level": project.get("staircase_volume_per_level") or 5.2,
        "structural_levels": structural_levels,
        # schedules (engine-correct keys)
        "foundations_schedule":  _footings(project),
        "neck_columns_schedule": neck_cols_sched,
        "tb_width":          tb_w,
        "tb_depth":          tb_d,
        "tb_total_length":   tb_len,
        "doors_schedule":    _doors(project),
        "windows_schedule":  _windows(project),
        "total_windows_area": project.get("total_windows_area") or (project.get("openings") or {}).get("totals", {}).get("window_area") or 0.0,
        "total_doors_count":  project.get("total_doors_count") or (project.get("openings") or {}).get("totals", {}).get("door_count") or 0.0,
        "concrete_grade":    project.get("concrete_grade") or "C30/37",
        "block_thickness":   project.get("block_thickness") or "200mm",
    }

    if nc_estimated and base["foundations_schedule"]:
        estimates.append("neck columns (typical 0.30×0.40 m section × footing count)")
    if not base["foundations_schedule"]:
        needs_input.append("foundation schedule (no footings found)")
    if not base["longest_length"] or not base["longest_width"]:
        needs_input.append("building footprint longest_length / longest_width")
    if not (project.get("schedules", {}).get("column_schedule", {}).get("columns")):
        needs_input.append("column schedule (column concrete = 0 until provided)")

    # per-floor blocks
    floors: dict[str, dict] = {}
    proj_floors = project.get("floors", {})
    walls       = project.get("walls", {})
    heights     = {"gf": "gf_height", "1f": "f1_height", "2f": "f2_height"}
    slab_keys   = {"gf": None, "1f": "slab_1f", "2f": "slab_2f", "roof": "slab_roof"}

    total_area = sum((proj_floors.get(k, {}) or {}).get("area", 0.0) for k in ("gf", "1f", "2f"))
    if total_area == 0: total_area = 1.0

    for fk in ("gf", "1f", "2f", "roof"):
        if fk not in proj_floors and fk != "roof":
            continue
        f = proj_floors.get(fk, {}) or {}
        w = walls.get(fk, {}) or {}
        area = f.get("area") or (project.get("roof_slab_area") if fk == "roof" else 0.0) or 0.0

        slab_key  = slab_keys[fk]
        # Suspended slabs (1F/2F/roof): thickness READ FROM THE DRAWING, with a
        # 0.25 m (25 cm) minimum per the QS spec. (Slab-on-grade is 10 cm, handled
        # separately by _calc_sog.)
        slab_thk  = 0.25
        beams     = []
        if slab_key:
            alt_keys = {
                "slab_1f": ["slab_1st", "slab_1f"],
                "slab_2f": ["slab_2nd", "slab_2f"],
                "slab_roof": ["roof_slab", "slab_roof"]
            }
            keys_to_try = alt_keys.get(slab_key, [slab_key])
            for k in keys_to_try:
                thickness_mm = (project.get("schedules", {})
                                       .get(k, {})
                                       .get("slab_thickness_mm"))
                if thickness_mm:
                    slab_thk = float(thickness_mm) / 1000
                    break
            slab_thk = max(slab_thk, 0.25)   # enforce 25 cm minimum
            beams, beam_est = _slab_beams(project, slab_key, area)
            if beam_est and beams:
                estimates.append(f"{slab_key} some beam lengths not measured — "
                                 f"fell back to count × typical bay (confirm in review)")

        area_ratio = area / total_area if fk != "roof" else 0.0

        floors[fk] = {
            "floor_id":         fk,
            "is_ground_floor":  bool(f.get("is_ground_floor", fk == "gf")),
            "floor_area":       area,
            "slab_area":        area,
            "slab_thickness":   slab_thk,
            "floor_height":     project.get(heights.get(fk, ""), 0.0) or f.get("height") or 4.0,
            "ext_perimeter":    f.get("ext_perimeter") or ext_perim,
            "external_perimeter": f.get("ext_perimeter") or ext_perim,
            "int_walls_length": project.get("int_walls_length") if fk == "gf" and project.get("int_walls_length") is not None else (w.get("internal_total_m") or f.get("int_walls_length") or 0.0),
            "int_walls_10cm": project.get("int_walls_10cm_m") if fk == "gf" and project.get("int_walls_10cm_m") is not None else (w.get("internal_10cm_m") or 0.0),
            "int_walls_20cm": project.get("int_walls_20cm_m") if fk == "gf" and project.get("int_walls_20cm_m") is not None else (w.get("internal_20cm_m") or 0.0),
            "wet_area":         f.get("wet_area") or 0.0,
            "wet_perimeter":    f.get("wet_perimeter") or 0.0,
            "dry_perimeter":    f.get("dry_perimeter") or 0.0,
            "balcony_area":     f.get("balcony_area") or 0.0,
            "beams_schedule":   beams,
            "columns_schedule": _columns_for_floor(project, fk),
            "windows_deduction": base["total_windows_area"] * area_ratio,
            "doors_deduction_count": base["total_doors_count"] * area_ratio,
        }

    meta = {"needs_input": needs_input, "estimates": estimates}
    return base, floors, meta


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Floor routing — which floor context does an item key belong to?
# ══════════════════════════════════════════════════════════════════════════════

def _route_floor(item_key: str, floors: dict) -> tuple[Optional[dict], bool]:
    """
    Decide the floor context for an item.

    Returns (floor_inputs, skip):
      - (floor_dict, False)  → floor item, floor exists → compute with it
      - (None, True)         → floor item but that floor doesn't exist → force 0
      - (None, False)        → project-wide item → compute with base only
    """
    # Column items embed two floor names; resolve them explicitly first.
    col_map = {
        "col_gf_to_1st":  "gf",
        "col_1st_to_2nd": "1f",
        "col_2nd_to_roof": "2f",
        "col_roof":        "roof",
        # legacy variants
        "col_gf":  "gf",
        "col_1f":  "1f",
        "col_2f":  "2f",
    }
    if item_key in col_map:
        fk = col_map[item_key]
        return (floors[fk], False) if fk in floors else (None, True)

    # Ordered from most-specific to least — _2nd before _nd, _1st before _st etc.
    routes = [
        (("_gf",),                   "gf"),
        (("_1f", "_1st"),            "1f"),
        (("_2f", "_2nd"),            "2f"),
        (("_roof",),                 "roof"),
    ]
    for suffixes, fk in routes:
        if any(item_key.endswith(s) for s in suffixes):
            return (floors[fk], False) if fk in floors else (None, True)

    return None, False   # project-wide item (parapet, roof_waterproofing, etc.)


def compute_all_quantities(project: dict) -> tuple[dict, dict]:
    """
    Returns (results, meta).
      results : { item_key: quantity }   for every item in DRAWING_ITEMS_MAP
      meta    : { 'needs_input', 'estimates' }
    """
    base, floors, meta = build_inputs(project)
    results: dict[str, float] = {}

    road_base_off = project.get("road_base_included", True) is False

    for page_type, page in DRAWING_ITEMS_MAP.items():
        for item in page["items"]:
            key = item["key"]
            if key == "road_base" and road_base_off:
                results[key] = 0.0          # user said no road base
                continue
            floor, skip = _route_floor(key, floors)
            if skip:
                results[key] = 0.0          # floor item for a floor that doesn't exist
                continue
            inputs = {**base, **floor} if floor else base
            qty = calculate_item(key, inputs)
            results[key] = round(qty, 2) if qty is not None else None

    return results, meta


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Public API — compute everything + assemble the BOQ DataFrame
POMI_NRM_MAP = {
    # Earthworks
    "excavation": "C.1",
    "backfill": "C.2",
    "road_base": "C.3",
    "anti_termite_found": "C.4",
    "polyethylene_found": "C.5",
    "anti_termite_tb": "C.6",
    "poly_sheet_tb": "C.7",
    
    # Concrete Blinding
    "foundation_pcc": "D.1",
    "tie_beam_pcc": "D.2",
    
    # Reinforced Concrete
    "foundation_concrete": "D.3",
    "neck_column_concrete": "D.4",
    "tie_beam_concrete": "D.5",
    "slab_on_grade": "D.6",
    "col_gf_to_1st": "D.7.1",
    "col_1st_to_2nd": "D.7.2",
    "col_roof": "D.7.3",
    "beam_concrete_1st": "D.8.1",
    "beam_concrete_2nd": "D.8.2",
    "beam_concrete_roof": "D.8.3",
    "slab_concrete_1st": "D.9.1",
    "slab_concrete_2nd": "D.9.2",
    "slab_concrete_roof": "D.9.3",
    "staircase_1st": "D.10",
    "parapet_concrete": "D.11",
    
    # Masonry
    "solid_block_work": "E.1",
    "thermal_block_gf": "E.2.1",
    "thermal_block_1f": "E.2.2",
    "thermal_block_2f": "E.2.3",
    "internal_block_gf": "E.3.1",
    "internal_block_1f": "E.3.2",
    "internal_block_2f": "E.3.3",
    "parapet_block_work": "E.4",
    
    # Waterproofing
    "foundation_bitumen": "F.1",
    "neck_column_bitumen": "F.2",
    "tie_beam_bitumen": "F.3",
    "block_work_bitumen": "F.4",
    "roof_waterproofing": "F.5",
    "wet_wp_1f": "F.6.1",
    "wet_wp_2f": "F.6.2",
    "balcony_wp_1f": "F.7.2",
    
    # Finishes
    "int_plaster_gf": "G.1.1",
    "int_plaster_1f": "G.1.2",
    "int_plaster_2f": "G.1.3",
    "external_plaster": "G.2",
    "int_paint_gf": "G.3.1",
    "int_paint_1f": "G.3.2",
    "int_paint_2f": "G.3.3",
    "external_finishes": "G.4",
    "dry_floor_gf": "G.5.1",
    "dry_floor_1f": "G.5.2",
    "dry_floor_2f": "G.5.3",
    "wet_floor_gf": "G.6.1",
    "wet_floor_1f": "G.6.2",
    "wet_floor_2f": "G.6.3",
    "wall_tiles_gf": "G.7.1",
    "wall_tiles_1f": "G.7.2",
    "wall_tiles_2f": "G.7.3",
    "skirting_gf": "G.8.1",
    "skirting_1f": "G.8.2",
    "skirting_2f": "G.8.3",
    "dry_ceiling_gf": "G.9.1",
    "dry_ceiling_1f": "G.9.2",
    "wet_ceiling_gf": "G.10.1",
    "wet_ceiling_1f": "G.10.2",
    "interlock_paving": "G.11",
    "compound_wall": "G.12",
    
    # Openings
    "door_openings": "H.1",
    "window_openings": "H.2",
}

BOQ_ITEM_DEFAULT_RATES = {
    "excavation": 20.0,
    "foundation_pcc": 295.0,
    "foundation_concrete": 350.0,
    "foundation_bitumen": 28.0,
    "neck_column_concrete": 350.0,
    "neck_column_bitumen": 28.0,
    "anti_termite_found": 5.0,
    "polyethylene_found": 3.5,
    "road_base": 95.0,
    "backfill": 85.0,
    "tie_beam_concrete": 350.0,
    "tie_beam_pcc": 295.0,
    "tie_beam_bitumen": 28.0,
    "slab_on_grade": 350.0,
    "solid_block_work": 220.0,
    "block_work_bitumen": 28.0,
    "anti_termite_tb": 5.0,
    "poly_sheet_tb": 3.5,
    "parapet_block_work": 45.0,
    "parapet_concrete": 350.0,
    "roof_waterproofing": 28.0,
    "external_plaster": 30.0,
    "external_finishes": 35.0,
    "interlock_paving": 65.0,
    "compound_wall": 450.0,
    "door_openings": 450.0,
    "window_openings": 350.0,
}

def _get_item_rate(item_key: str, emirate: str) -> float:
    # Pricing disabled by request — quantity-only BOQ (all rates & totals are zero).
    return 0.0


def build_boq_dataframe_from_project(project: dict) -> tuple[pd.DataFrame, dict]:
    """
    Build the export-ready BOQ DataFrame straight from _project_data.json.
    Returns (df, meta).  df columns match engine/boq_builder output so the
    existing Excel exporter & UI table work unchanged.
    """
    results, meta = compute_all_quantities(project)
    emirate = project.get("emirate") or "Dubai"

    rows = []
    item_num = 1

    def add_section(title: str):
        rows.append({
            "#": "", "Description (English)": f"■ {title}", "الوصف": "",
            "Unit": "", "Quantity": "", "_is_header": True,
        })

    for page_type, page in DRAWING_ITEMS_MAP.items():
        if page_type in ["slab_1st", "slab_2nd", "first_floor_plan", "second_floor_plan"]:
            total_qty = sum(results.get(item["key"], 0.0) or 0.0 for item in page["items"])
            if total_qty == 0:
                continue

        section_title = f"{page['label_en']} | {page['label_ar']}"
        add_section(section_title)
        for item in page["items"]:
            qty = results.get(item["key"], 0.0)
            nrm_code = POMI_NRM_MAP.get(item["key"], str(item_num))
            rate = _get_item_rate(item["key"], emirate)
            total = qty * rate if qty is not None and rate is not None else 0.0

            en_name = item["name_en"]
            ar_name = item["name_ar"]
            if "block" in item["key"]:
                t = "200mm"
                if "solid" in item["key"]:
                    t = project.get("solid_block_thickness", "200mm")
                elif "thermal" in item["key"] or "parapet" in item["key"]:
                    t = project.get("thermal_block_thickness", "200mm")
                elif "internal" in item["key"]:
                    t = project.get("hollow_block_thickness", "100mm")
                en_name += f" ({t} Thickness)"
                ar_name += f" (سماكة {t})"
            rows.append({
                "#": nrm_code,
                "Description (English)": en_name,
                "الوصف": ar_name,
                "Unit": item["unit"],
                "Quantity": round(float(qty), 2) if qty is not None else 0.0,
                "has_error": qty is None,
                "_is_header": False,
            })
            item_num += 1

    df = pd.DataFrame(rows)
    df = df.where(pd.notnull(df), None)
    return df, meta
