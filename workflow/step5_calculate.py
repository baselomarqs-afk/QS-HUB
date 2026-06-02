"""
STEP 5 — Apply Formulas
Takes all extracted + confirmed values
Applies exact formulas → gets quantities
"""

from engine.substructure   import calc_all_substructure
from engine.superstructure import calc_all_superstructure
from engine.finishes       import calc_villa_finishes
from engine.openings       import calc_doors, calc_windows
from workflow.workflow_state import mark_step_done


def _get(results, drawing_type, field, fallback=0.0, state=None):
    for r in results.values():
        if r.get("drawing_type") == drawing_type:
            v = r.get(field)
            if v is not None:
                try:
                    return float(v)
                except Exception:
                    pass
    if state:
        return state.get(f"manual_{drawing_type}_{field}",
               state.get(field, fallback))
    return fallback


def _get_list(results, drawing_type, field):
    # Same type may appear on several pages — keep the RICHEST list
    # (e.g. one foundation page returns an empty footings list, another the full one).
    best = []
    for r in results.values():
        if r.get("drawing_type") == drawing_type:
            v = r.get(field)
            if isinstance(v, list) and len(v) > len(best):
                best = v
    return best


def _build_floor_slabs(num_floors, g, gl, floor_cols, areas, struct_gf_area=0.0):
    """
    Map suspended slabs to the occupied floors WITHOUT double-counting the roof.
    A G+N villa has exactly N+1 occupied levels and N+1 suspended slabs
    (1st-floor slab … roof slab). The TOP floor's slab IS the roof slab; the
    standalone 'roof' entry only carries the parapet (slab_area = 0).
        gf  -> slab_1st        (1st-floor slab)
        f1  -> slab_2nd        (2nd-floor slab)
        f2  -> roof_slab       (roof slab, above 2nd floor) — for G+2
    """
    floor_keys = ["gf", "f1", "f2"][:num_floors]
    slab_src = {"gf": "slab_1st", "f1": "slab_2nd", "f2": "roof_slab"}
    plan_src = {"gf": "ground_floor_plan", "f1": "first_floor_plan", "f2": "second_floor_plan"}
    col_suf  = {"gf": "gf", "f1": "1f", "f2": "2f"}
    top = floor_keys[-1]
    out = {}
    for fk in floor_keys:
        sk = "roof_slab" if fk == top else slab_src[fk]   # top floor slab = roof slab
        
        # thickness fallback: confirmed override -> AI extraction -> 0.25. Minimum realistic slab is 0.20m.
        thk_override = float(areas.get(col_suf[fk], {}).get("thk") or 0)
        thk = thk_override if thk_override > 0 else g(sk, "slab_thickness", 0.25)
        if thk < 0.20:
            thk = 0.25
        
        # area fallback: confirmed architectural area -> generic architectural plan -> structural extraction
        area_override = float(areas.get(col_suf[fk], {}).get("area") or 0)
        slab_area = area_override if area_override > 0 else (g(plan_src[fk], "total_floor_area") or g(sk, "slab_area") or struct_gf_area)
        
        # Protection against absurdly small slab panels being mistakenly extracted as the whole floor area
        # (Removed Bullshit Filter for suspended beams: AI must extract or user must verify manually)
        beams = gl(sk, "beams")
        beam_len = sum(float(b.get("length", 0) or 0) for b in beams) if beams else 0

        out[fk] = {
            "slab_area":      slab_area,
            "slab_thickness": thk,
            "columns":        floor_cols(col_suf[fk]),
            "beams":          beams,
        }
    
    # Parapet-only standalone 'roof' uses the top floor's thickness if needed (usually 0)
    top_thk = float(areas.get(col_suf[top], {}).get("thk") or 0) or 0.25
    roof_beams = gl("roof_slab", "beams")
    if roof_beams:
        rb_len = sum(float(b.get("length", 0) or 0) for b in roof_beams)
            
    out["roof"] = {
        "slab_area": g("roof_slab", "slab_area", 0.0), "slab_thickness": top_thk,
        "columns": floor_cols("roof"), "beams": roof_beams,
        "roof_perimeter": g("ground_floor_plan", "ext_perimeter") or g("tie_beam", "ext_perimeter") or g("roof_slab", "roof_perimeter"),
    }
    return out


def _ss(state, key, default):
    """Safe state-dict read (framework-agnostic)."""
    if state is None:
        return default
    return state.get(key, default)


def _finish_inputs(num_floors, g, heights, areas, struct_gf_area=0.0, struct_ext_perim=0.0):
    """
    Finishes inputs driven by the confirmed floor areas (Step 4 / passed in) with an
    aggressive multi-level fallback chain so finishes are NEVER zero:

    Floor area resolution order:
      1. Confirmed area from Step 4 (ci_area_xx)
      2. AI extraction from architectural plan (ground_floor_plan → total_floor_area)
      3. Structural GF area (from tie beam / foundation – works for ALL floors as
         UAE villas typically have equal or near-equal floor plates)

    Wet area resolution:
      1. Confirmed wet area from Step 4
      2. AI extraction from architectural plan
      3. Auto-estimate: 18% of floor_area (typical UAE villa wet/dry ratio)

    Perimeters & wall lengths:
      1. AI extraction from architectural plan
      2. Structural ext_perimeter (from tie beam layout)
      3. Geometric estimate:  ext_perimeter ≈ 4.2·√floor_area
                              wet_perimeter ≈ 4.0·√wet_area
                              dry_perimeter ≈ 4.2·√dry_area
                              int_walls     ≈ 0.35·floor_area
    """
    PLAN = {"gf": "ground_floor_plan", "f1": "first_floor_plan", "f2": "second_floor_plan"}
    CI   = {"gf": "gf", "f1": "1f", "f2": "2f"}
    areas = areas or {}
    out = {}

    # Resolve the best available GF area once (used as fallback for upper floors)
    _best_gf_area = (
        float((areas.get("gf") or {}).get("area") or 0)
        or g("ground_floor_plan", "total_floor_area")
        or struct_gf_area
    )
    # Best available ext_perimeter (structural is very reliable — from tie beam layout)
    _best_ext_perim = (
        struct_ext_perim
        or g("tie_beam", "ext_perimeter")
        or g("ground_floor_plan", "ext_perimeter")
    )

    for fk in ["gf", "f1", "f2"][:num_floors]:
        plan, ci = PLAN[fk], CI[fk]
        ov = areas.get(ci, {}) or {}

        # ── Floor area: confirmed → AI arch plan → structural GF area fallback ──
        fa = (
            float(ov.get("area") or 0)
            or g(plan, "total_floor_area")
            or _best_gf_area     # UAE villas: upper floors ≈ GF area
        )
        
        if fa < _best_gf_area * 0.5:
            fa = _best_gf_area

        # ── Wet area: confirmed → AI → auto-estimate 18% of floor area ──────────
        wa = (
            float(ov.get("wet") or 0)
            or g(plan, "wet_area")
            or round(fa * 0.18, 2)   # typical UAE villa: ~18% wet rooms
        )

        dry = max(fa - wa, 0.0)

        # ── Ext perimeter: confirmed → AI → structural → geometric ──────────────
        extp = (
            float(ov.get("ext") or 0)
            or g(plan, "ext_perimeter")
            or _best_ext_perim
            or (round(4.2 * (fa ** 0.5), 2) if fa else 0.0)
        )

        # ── Wet perimeter: AI → geometric from wet area ─────────────────────────
        wetp = g(plan, "wet_perimeter") or (round(4.0 * (wa ** 0.5), 2) if wa else 0.0)

        # ── Dry perimeter: AI → geometric from dry area ─────────────────────────
        dryp = g(plan, "dry_perimeter") or (round(4.2 * (dry ** 0.5), 2) if dry else 0.0)

        # ── Internal walls length: confirmed → AI → 0.0 (must not estimate!) ──
        intw = (
            float(ov.get("int") or 0)
            or g(plan, "int_walls_length")
            or 0.0
        )

        out[fk] = {
            "floor_area": fa, "wet_area": wa, "wet_perimeter": wetp,
            "dry_perimeter": dryp, "ext_perimeter": extp,
            "int_walls_length": intw, "balcony_area": g(plan, "balcony_area"),
            "height": heights[fk],
        }
    out["balcony_area"] = sum(out[fk]["balcony_area"] for fk in out if isinstance(out.get(fk), dict))
    return out


def _normalize_openings(items: list) -> list:
    """
    Normalize door/window list from extraction results:
    - COUNT: prefer count_in_plans (authoritative, from floor plans via fitz).
             Fall back to schedule count if plan count is absent.
    - DIMENSIONS: convert width_mm/height_mm → metres where applicable.
    """
    out = []
    for o in (items or []):
        count = o.get("count_in_plans") or o.get("count", 0) or 0
        # Dimension resolution: _mm fields → metres; else legacy metre fields
        if o.get("width_mm"):
            w_mm = float(o["width_mm"])
            width_m = round(w_mm / 1000.0, 4) if w_mm > 50 else w_mm
        else:
            w = o.get("width_m") or o.get("width") or 0
            width_m  = round(float(w) / 1000.0, 4) if float(w or 0) > 50 else float(w or 0)
        if o.get("height_mm"):
            h_mm = float(o["height_mm"])
            height_m = round(h_mm / 1000.0, 4) if h_mm > 50 else h_mm
        else:
            h = o.get("height_m") or o.get("height") or o.get("length") or 0
            height_m = round(float(h) / 1000.0, 4) if float(h or 0) > 50 else float(h or 0)
        out.append({
            "mark":     o.get("mark", ""),
            "width_m":  width_m,
            "height_m": height_m,
            "count":    count,
            "count_source": o.get("count_source", "schedule_only"),
        })
    return out


def build_inputs_from_results(results: dict, num_floors=None, heights=None, areas=None, state=None) -> dict:
    """
    Build the full engine-input dict from extraction results.
    Used by BOTH the API layer and headless tests — values come from the
    arguments when given, else from the state dict (so there is ONE code path).
    """
    g = lambda dt, f, fb=0.0: _get(results, dt, f, fb, state=state)
    gl = lambda dt, f: _get_list(results, dt, f)

    if num_floors is None:
        num_floors = int(_ss(state, "num_floors", 2))
        
    # Failsafe: if AI mistakenly flagged as G-only but extracted upper floors
    if num_floors == 1:
        has_f1 = any(r.get("drawing_type") in ("first_floor_plan", "slab_2nd", "columns_1f") for r in results.values())
        if has_f1 or g("first_floor_plan", "total_floor_area") > 0:
            num_floors = 2
            
    if heights is None:
        heights = {"gf": _ss(state, "gf_height", 4.0), "f1": _ss(state, "f1_height", 4.0), "f2": _ss(state, "f2_height", 4.0)}
    if areas is None:
        areas = {ci: {
            "area": _ss(state, f"ci_area_{ci}", 0),
            "wet": _ss(state, f"ci_wet_{ci}", 0),
            "thk": _ss(state, f"ci_thk_{ci}", 0),
            "ext": _ss(state, f"ci_ext_{ci}", 0),
            "int": _ss(state, f"ci_int_{ci}", 0)
        } for ci in ("gf", "1f", "2f")}

    gf_h, f1_h, f2_h = heights["gf"], heights["f1"], heights["f2"]
    total_h = gf_h + (f1_h if num_floors >= 2 else 0) + (f2_h if num_floors >= 3 else 0)

    # ── Per-floor columns: each floor gets ONLY its own column count ──────────
    cols_all = (gl("upper_columns", "columns") or []) + (gl("column_schedule", "columns") or [])
    # dedicated single-floor column pages
    _PERFLOOR_PAGE = {"gf": "ground_columns", "1f": "columns_1f",
                      "2f": "columns_2f", "roof": "columns_roof"}

    def _floor_cols(suffix: str) -> list:
        # 1) combined schedule with per-floor counts
        out = []
        for c in cols_all:
            cnt = c.get(f"count_{suffix}", 0) or 0
            if not cnt and (c.get("count", 0) or 0) and suffix != "roof":
                cnt = c.get("count", 0) or 0
            if cnt:
                out.append({
                    "length": float(c.get("length_m") or c.get("length") or 0.60),
                    "width":  float(c.get("width_m")  or c.get("width")  or 0.20),
                    "count":  cnt,
                })
        if out:
            return out
        # 2) dedicated single-floor column page (single count per mark)
        # For GF, try ground_columns first, then neck_columns
        target_page = _PERFLOOR_PAGE.get(suffix, "")
        page_cols = gl(target_page, "columns")
        if not page_cols and suffix == "gf":
            page_cols = gl("neck_columns", "columns")
            
        out2 = [{
            "length": float(c.get("length_m") or c.get("length") or 0.60),
            "width":  float(c.get("width_m")  or c.get("width")  or 0.20),
            "count":  c.get("count", 0) or 0,
        } for c in page_cols if (c.get("count", 0) or 0)]
        if out2:
            return out2
            
        # 3) ULTIMATE FALLBACK: Estimate geometrically if AI completely failed
        # _struct_gf_area is evaluated outside and captured in closure
        divisor = 20.0 if suffix == "roof" else 15.0
        est_cnt = max(4, int(_struct_gf_area / divisor)) if _struct_gf_area else 16
        return [{
            "length": 0.60,
            "width":  0.20,
            "count":  est_cnt,
        }]

    # ── Pre-compute structural values (available from tie beam / foundation) ──
    _ll = g("foundations", "longest_length")
    _lw = g("foundations", "longest_width")
    _geom_floor_area = round(_ll * _lw * 0.75, 2) if _ll and _lw else 0.0

    # 1. GF Area Bullshit Filter
    _struct_gf_area = float(areas.get("gf", {}).get("area") or 0)
    if not _struct_gf_area:
        _ai_gf_area = g("ground_floor_plan", "total_floor_area") or g("tie_beam", "gf_area")
        if _ai_gf_area and _geom_floor_area and _ai_gf_area < _geom_floor_area * 0.5:
            _struct_gf_area = _geom_floor_area  # AI extracted bullshit (e.g. Majlis area only)
        else:
            _struct_gf_area = _ai_gf_area or _geom_floor_area

    # 2. Ext Perimeter Bullshit Filter
    _struct_ext_perim = g("tie_beam", "ext_perimeter") or g("ground_floor_plan", "ext_perimeter")
    _geom_perim = round(4.2 * (_struct_gf_area ** 0.5), 2) if _struct_gf_area else 0.0
    if not _struct_ext_perim or _struct_ext_perim < _geom_perim * 0.6:
        _struct_ext_perim = _geom_perim

    # 3. Tie Beam Length Bullshit Filter
    tb_beams = gl("tie_beam", "beams")
    tb_len = g("tie_beam", "tb_total_length")
    if not tb_len and tb_beams:
        tb_len = sum(float(b.get("length", 0) or 0) for b in tb_beams)
        
    int_wall_len = float(areas.get("gf", {}).get("int") or 0) or g("ground_floor_plan", "int_walls_length")
    if not int_wall_len:
        int_wall_len = 0.0 # Force manual input if missing
        
    _geom_tb_len = _struct_ext_perim + int_wall_len
    if not tb_len or tb_len < _geom_tb_len * 0.5:
        tb_len = _geom_tb_len
        tb_beams = []  # Discard extracted beam array if the total length is hallucinated

    # Openings fallback if schedules are empty
    doors_list = _normalize_openings(gl("schedules", "doors"))
    windows_list = _normalize_openings(gl("schedules", "windows"))
    
    total_fa = 0.0
    for fk in ["gf", "1f", "2f"][:num_floors]:
        plan = {"gf": "ground_floor_plan", "1f": "first_floor_plan", "2f": "second_floor_plan"}[fk]
        fa = float(areas.get(fk, {}).get("area") or 0) or g(plan, "total_floor_area") or _struct_gf_area
        total_fa += fa

    if not doors_list or sum(d.get("count", 0) for d in doors_list) == 0:
        est_door_count = max(int(total_fa / 15.0), 6 * num_floors) if total_fa else 12
        doors_list = [{
            "mark": "D_EST",
            "width_m": 0.9,
            "height_m": 2.1,
            "count": est_door_count,
            "count_source": "estimated_fallback"
        }]

    if not windows_list or sum(w.get("count", 0) for w in windows_list) == 0:
        est_window_count = max(int(total_fa / 20.0), 4 * num_floors) if total_fa else 8
        windows_list = [{
            "mark": "W_EST",
            "width_m": 1.5,
            "height_m": 1.5,
            "count": est_window_count,
            "count_source": "estimated_fallback"
        }]

    return {
        # Sub-structure
        "foundations":    gl("foundations", "footings") or gl("foundations", "foundations"),
        # Neck columns = the GROUND-FLOOR columns (each GF column has a neck
        # between footing and tie beam). Same size/count, neck height 1.0 m.
        "neck_columns":   _floor_cols("gf") or gl("foundations", "neck_columns"),
        "tb_width":       max(float(g("tie_beam", "typical_tb_width", g("tie_beam", "tb_width", 0.20))), 0.20),
        "tb_depth":       max(float(g("tie_beam", "typical_tb_depth", g("tie_beam", "tb_depth", 0.60))), 0.50),
        "tb_length":      tb_len,
        "tb_beams":       tb_beams,
        "ext_perimeter":  _struct_ext_perim,
        "gf_area":        _struct_gf_area,
        "longest_length": g("foundations", "longest_length"),
        "longest_width":  g("foundations", "longest_width"),

        # Super-structure
        "num_floors":     num_floors,
        "floors": _build_floor_slabs(num_floors, g, gl, _floor_cols, areas, struct_gf_area=_struct_gf_area),
        # structural_levels: use confirmed num_floors (Step 4) as primary source;
        # slab_1st extraction is unreliable / often absent.
        "structural_levels": num_floors,

        # Finishes (auto-calculated: structural fallback → geometric estimate → never zero)
        "finishes": _finish_inputs(num_floors, g, {"gf": gf_h, "f1": f1_h, "f2": f2_h}, areas,
                                   struct_gf_area=_struct_gf_area,
                                   struct_ext_perim=_struct_ext_perim),
        "roof_area": (
            g("roof_floor_plan", "roof_slab_area") 
            or float(areas.get(["gf", "1f", "2f"][:num_floors][-1], {}).get("area") or 0)
            or g({"gf": "ground_floor_plan", "1f": "first_floor_plan", "2f": "second_floor_plan"}.get(["gf", "1f", "2f"][:num_floors][-1]), "total_floor_area")
            or g("roof_slab", "slab_area")
        ),
        "total_height":     total_h,

        # Openings — dimensions from schedule, count from floor plans (plan count is authoritative)
        "doors":   doors_list,
        "windows": windows_list,

        # Setting out — prefer state dict (set in Step 4) over AI extraction
        "plot_area":       (
            float(_ss(state, "plot_area", 0) or 0)
            or g("setting_out", "plot_area")
        ),
        "compound_length": (
            float(_ss(state, "compound_length", 0) or 0)
            or g("setting_out", "compound_length")
        ),
    }


def compute_boq(results: dict, num_floors=None, heights=None, areas=None, state=None) -> dict:
    """
    THE single calculation path used by BOTH the UI and headless tests.
    Builds inputs → runs every engine formula → returns all result groups + BOQ df.
    """
    from engine.boq_builder import build_boq_dataframe
    inputs = build_inputs_from_results(results, num_floors, heights, areas, state=state)
    sub   = calc_all_substructure(inputs)
    sup   = calc_all_superstructure(inputs["floors"], inputs["num_floors"])
    fin   = calc_villa_finishes(inputs["finishes"], inputs["num_floors"],
                                inputs.get("ext_perimeter", 0), inputs.get("total_height", 12),
                                inputs.get("roof_area", 0), inputs["finishes"].get("balcony_area", 0))
    opens = {"doors": calc_doors(inputs.get("doors", [])),
             "windows": calc_windows(inputs.get("windows", []))}
    setout = {
        "interlock": max(
            (inputs.get("plot_area") or _ss(state, "plot_area", 0))
            - (inputs.get("gf_area") or 0),
            0
        ),
        "compound_wall": (
            inputs.get("compound_length")
            or _ss(state, "compound_length", 0)
        ),
    }
    boq_df = build_boq_dataframe(sub, sup, fin, opens, inputs["num_floors"], setout)
    return {"inputs": inputs, "sub": sub, "super": sup, "finish": fin,
            "openings": opens, "setting_out": setout, "boq_df": boq_df}



