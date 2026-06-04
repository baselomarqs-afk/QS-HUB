import os
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from utils.db import safe_query, safe_execute

router = APIRouter()

class ConfirmDataReq(BaseModel):
    project_id: int
    confirmed_data: Dict[str, Any]

def reconstruct_project_inputs(state_data: dict):
    confirmed = state_data.get("confirmed_auto_data") or {}
    ext_res = state_data.get("extraction_results") or {}
    
    # Reconstruct schedules if missing or empty
    schedules = confirmed.get("schedules") or {}
    for page_key, page in ext_res.items():
        if not isinstance(page, dict) or not page.get("_ok"):
            continue
        dtype = page.get("drawing_type") or page.get("detected_type")
        if not dtype:
            continue
            
        if dtype == "foundations":
            # Prefer the foundation page that actually carries footings — an empty
            # duplicate page (same dtype) must NOT override the real schedule.
            new_footings = page.get("footings") or []
            existing = (schedules.get("foundation") or {}).get("footings") or []
            if (new_footings and len(new_footings) >= len(existing)) or "foundation" not in schedules:
                schedules["foundation"] = {"footings": new_footings}
        elif dtype in ("column_schedule", "upper_columns", "neck_columns") or dtype.startswith("columns"):
            # The classifier also emits per-floor column types (columns_gf/1f/2f/roof);
            # accept them all and keep the page with the most columns.
            new_cols = page.get("columns") or []
            existing = (schedules.get("column_schedule") or {}).get("columns") or []
            if (new_cols and len(new_cols) >= len(existing)) or "column_schedule" not in schedules:
                schedules["column_schedule"] = {"columns": new_cols}
        elif dtype == "tie_beam":
            # Tie beam extraction → pick up tb dimensions into schedule
            tb_entry = schedules.get("tie_beam", {})
            if not tb_entry.get("tie_beams"):
                # Build a single tie-beam entry from the flat extraction values
                tb_w = page.get("tb_width")
                tb_d = page.get("tb_depth")
                tb_len = page.get("tb_total_length")
                if tb_w or tb_d:
                    tb_entry["tie_beams"] = [{
                        "type": "TB1",
                        "width_mm": round(float(tb_w or 0.30) * 1000),
                        "depth_mm": round(float(tb_d or 0.60) * 1000),
                        "length_m": float(tb_len or 0),
                        "count_segments": 1,
                    }]
                # Also store flat values for direct access by the bridge
                if tb_w: tb_entry["tb_width"] = float(tb_w)
                if tb_d: tb_entry["tb_depth"] = float(tb_d)
                if tb_len: tb_entry["tb_total_length"] = float(tb_len)
                schedules["tie_beam"] = tb_entry
        elif dtype in ["slab_1st", "slab_2nd", "roof_slab"]:
            new_beams = page.get("beams") or []
            existing = (schedules.get(dtype) or {}).get("beams") or []
            if (dtype not in schedules) or (new_beams and len(new_beams) >= len(existing)):
                schedules[dtype] = {"beams": new_beams, "slab_thickness_mm": ((page.get("slab_thickness") or 0.2) * 1000)}
                
    confirmed["schedules"] = schedules

    # Reconstruct openings if missing or empty
    openings = confirmed.get("openings") or {}
    if "totals" not in openings:
        openings["totals"] = {"door_count": 0, "window_area": 0.0}
        
    for page_key, page in ext_res.items():
        if not isinstance(page, dict) or not page.get("_ok"):
            continue
        dtype = page.get("drawing_type") or page.get("detected_type")
        if dtype in ["schedules", "door_schedule", "window_schedule"]:
            if "doors" not in openings and page.get("doors"):
                openings["doors"] = page["doors"]
                # Sum door count from the schedule
                for d in page["doors"]:
                    qty = int(d.get("count_in_plans") or d.get("count") or d.get("qty") or d.get("quantity") or 1)
                    openings["totals"]["door_count"] += qty
                    
            if "windows" not in openings and page.get("windows"):
                openings["windows"] = page["windows"]
                # Sum window area from the schedule
                for w in page["windows"]:
                    qty = int(w.get("count_in_plans") or w.get("count") or w.get("qty") or w.get("quantity") or 1)
                    width = float(w.get("width") or w.get("width_m") or 1.0)
                    height = float(w.get("height") or w.get("height_m") or 1.0)
                    # If dimensions are in mm, convert to m
                    if width > 10: width /= 1000.0
                    if height > 10: height /= 1000.0
                    openings["totals"]["window_area"] += (qty * width * height)
        
        # Aggregate direct visual counts from floor plans if they exist
        if dtype in ["ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan"]:
            doors = page.get("total_doors_count")
            if doors is not None:
                try: openings["totals"]["door_count"] += int(doors)
                except: pass
            
            windows = page.get("total_windows_area")
            if windows is not None:
                try: openings["totals"]["window_area"] += float(windows)
                except: pass
                
    confirmed["openings"] = openings

    # Reconstruct floors and walls
    floors = confirmed.get("floors") or {}
    walls = confirmed.get("walls") or {}
    
    floor_map = {
        "ground_floor_plan": "gf",
        "first_floor_plan": "1f",
        "second_floor_plan": "2f",
        "roof_floor_plan": "roof"
    }
    
    for page_key, page in ext_res.items():
        if not isinstance(page, dict) or not page.get("_ok"):
            continue
        dtype = page.get("drawing_type") or page.get("detected_type")
        if dtype in floor_map:
            fk = floor_map[dtype]
            if fk not in floors or not floors[fk].get("area"):
                floors[fk] = {
                    "area": page.get("total_floor_area") or page.get("floor_area") or 0.0,
                    "ext_perimeter": page.get("ext_perimeter") or 0.0,
                    "wet_area": page.get("wet_area") or 0.0,
                    "wet_perimeter": page.get("wet_perimeter") or 0.0,
                    "dry_perimeter": page.get("dry_perimeter") or 0.0,
                    "balcony_area": page.get("balcony_area") or page.get("balcony_terrace_area_m2") or 0.0,
                    "height": page.get("floor_height") or page.get("floor_height_m") or 4.0
                }
            if fk not in walls or not walls[fk].get("internal_total_m"):
                walls[fk] = {
                    "internal_total_m": page.get("int_walls_length") or 0.0,
                    "internal_10cm_m": page.get("int_walls_10cm_m") or 0.0,
                    "internal_20cm_m": page.get("int_walls_20cm_m") or 0.0,
                }
                
    confirmed["floors"] = floors
    confirmed["walls"] = walls
    
    # Heal and sanitize flat fields if empty or overwritten
    sources = confirmed.get("sources") or {}
    for page_key, page in ext_res.items():
        if not isinstance(page, dict) or not page.get("_ok"):
            continue
        dtype = page.get("drawing_type") or page.get("detected_type")
        if dtype == "ground_floor_plan":
            if not confirmed.get("gf_area") or confirmed.get("gf_area") < 30.0:
                confirmed["gf_area"] = page.get("total_floor_area") or page.get("floor_area") or 0.0
                sources["gf_area"] = "AI OCR"
            elif "gf_area" not in sources:
                sources["gf_area"] = "AI OCR"
                
            if not confirmed.get("ext_perimeter") or confirmed.get("ext_perimeter") < 15.0:
                confirmed["ext_perimeter"] = page.get("ext_perimeter") or 0.0
                sources["ext_perimeter"] = "AI OCR"
            elif "ext_perimeter" not in sources:
                sources["ext_perimeter"] = "AI OCR"
        elif dtype == "roof_floor_plan" or dtype == "roof_slab":
            if not confirmed.get("roof_perimeter") or confirmed.get("roof_perimeter") == 0.0:
                confirmed["roof_perimeter"] = page.get("roof_perimeter") or page.get("ext_perimeter") or 0.0
                sources["roof_perimeter"] = "AI OCR"
            elif "roof_perimeter" not in sources:
                sources["roof_perimeter"] = "AI OCR"
                
            if not confirmed.get("roof_slab_area") or confirmed.get("roof_slab_area") == 0.0:
                confirmed["roof_slab_area"] = page.get("slab_area") or page.get("total_floor_area") or 0.0
                sources["roof_slab_area"] = "AI OCR"
            elif "roof_slab_area" not in sources:
                sources["roof_slab_area"] = "AI OCR"
        elif dtype == "setting_out":
            if not confirmed.get("plot_area") or confirmed.get("plot_area") == 0.0:
                confirmed["plot_area"] = page.get("plot_area") or 0.0
                sources["plot_area"] = "AI OCR"
            elif "plot_area" not in sources:
                sources["plot_area"] = "AI OCR"
                
            if not confirmed.get("compound_length") or confirmed.get("compound_length") == 0.0:
                confirmed["compound_length"] = page.get("compound_length") or 0.0
                sources["compound_length"] = "AI OCR"
            elif "compound_length" not in sources:
                sources["compound_length"] = "AI OCR"
                
        # Copy internal walls to flat keys so VerifyStep.jsx can read them
        if dtype in ["ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan"]:
            val_10 = float(page.get("int_walls_10cm_m") or 0.0)
            val_20 = float(page.get("int_walls_20cm_m") or 0.0)
            
            # If the AI failed to explicitly find them, use the geometric mathematical total
            # calculated by step3_extract.py (int_walls_length) as 20cm walls.
            if val_10 == 0 and val_20 == 0:
                val_20 = float(page.get("int_walls_length") or 0.0)
            if "int_walls_10cm_m" not in sources or sources["int_walls_10cm_m"] == "AI OCR":
                if val_10 > 0:
                    confirmed["int_walls_10cm_m"] = confirmed.get("int_walls_10cm_m", 0.0) + val_10
                    sources["int_walls_10cm_m"] = "AI OCR"
            if "int_walls_20cm_m" not in sources or sources["int_walls_20cm_m"] == "AI OCR":
                if val_20 > 0:
                    confirmed["int_walls_20cm_m"] = confirmed.get("int_walls_20cm_m", 0.0) + val_20
                    sources["int_walls_20cm_m"] = "AI OCR"


    # Heal building dimensions from ANY page that carries them —
    # the foundation page reports longest_length/width, the tie_beam page
    # reports gf_area and ext_perimeter, etc.  Pick up real AI-extracted
    # values from wherever they exist instead of leaving them as 0.
    _ANY_PAGE_FIELDS = (
        "longest_length", "longest_width", "total_villa_height",
        "gf_area", "ext_perimeter",
    )
    # Map: some pages use different key names for the same concept
    _FIELD_ALIASES = {
        "gf_area": ("gf_area", "total_floor_area", "floor_area"),
        "ext_perimeter": ("ext_perimeter", "external_perimeter"),
    }
    for page_key, page in ext_res.items():
        if not isinstance(page, dict) or not page.get("_ok"):
            continue
        for field in _ANY_PAGE_FIELDS:
            if confirmed.get(field) and float(confirmed.get(field) or 0) > 0:
                continue  # already have a real value
            # Try field name and aliases
            aliases = _FIELD_ALIASES.get(field, (field,))
            for alias in aliases:
                val = page.get(alias)
                if val and float(val) > 0:
                    confirmed[field] = float(val)
                    break

    for field in _ANY_PAGE_FIELDS:
        if confirmed.get(field) and field not in sources:
            sources[field] = "AI OCR"

    # ── CROSS-FIELD: ext_perimeter = 2(L+W) — this IS correct rectangle geometry ─
    import math

    _ll = float(confirmed.get("longest_length") or 0)
    _lw = float(confirmed.get("longest_width") or 0)
    
    # gf_area fallback from foundation dimensions
    if (not confirmed.get("gf_area") or float(confirmed.get("gf_area") or 0) < 30) and _ll and _lw:
        confirmed["gf_area"] = round(_ll * _lw * 0.75, 2)
        sources["gf_area"] = "Geometry L×W×0.75"
    if (not confirmed.get("ext_perimeter") or float(confirmed.get("ext_perimeter") or 0) < 10) and _ll and _lw:
        confirmed["ext_perimeter"] = round(2 * (_ll + _lw), 2)
        if "ext_perimeter" not in sources or sources["ext_perimeter"] == "AI OCR":
            sources["ext_perimeter"] = "Geometry 2(L+W)"

    # ── HEAL MISSING FLOOR MAPPING ──
    # If ground_floor_plan extraction completely failed, floors["gf"] will be missing,
    # causing all ground floor items to be skipped. If the user manually provided gf_area,
    # we MUST initialize floors["gf"] to ensure execution.
    if confirmed.get("gf_area") and float(confirmed.get("gf_area")) > 0:
        if "gf" not in confirmed["floors"]:
            confirmed["floors"]["gf"] = {}
        if not confirmed["floors"]["gf"].get("area"):
            confirmed["floors"]["gf"]["area"] = float(confirmed["gf_area"])
    
    if confirmed.get("ext_perimeter") and float(confirmed.get("ext_perimeter")) > 0:
            confirmed["floors"]["gf"]["ext_perimeter"] = float(confirmed["ext_perimeter"])

    # ── FALLBACKS FOR ROOF, PLOT, AND INTERNAL WALLS ──
    if not confirmed.get("roof_perimeter") or confirmed.get("roof_perimeter") == 0.0:
        confirmed["roof_perimeter"] = confirmed.get("ext_perimeter", 0.0)
        if "roof_perimeter" not in sources:
            sources["roof_perimeter"] = "Geometry Fallback (ext_perimeter)"

    if not confirmed.get("roof_slab_area") or confirmed.get("roof_slab_area") == 0.0:
        confirmed["roof_slab_area"] = confirmed.get("gf_area", 0.0)
        if "roof_slab_area" not in sources:
            sources["roof_slab_area"] = "Geometry Fallback (gf_area)"
            
    if not confirmed.get("plot_area") or confirmed.get("plot_area") == 0.0:
        if confirmed.get("gf_area") and confirmed["gf_area"] > 0:
            confirmed["plot_area"] = round(confirmed["gf_area"] * 2.5, 2)
            sources["plot_area"] = "Geometry Fallback (GF×2.5)"

    # GEOMETRIC FALLBACK FOR INTERNAL WALLS:
    val_10 = float(confirmed.get("int_walls_10cm_m") or 0.0)
    val_20 = float(confirmed.get("int_walls_20cm_m") or 0.0)
    if val_10 == 0 and val_20 == 0:
        total_bua = sum(float(f.get("area", 0)) for f in confirmed.get("floors", {}).values())
        if total_bua == 0 and confirmed.get("gf_area"):
            total_bua = float(confirmed["gf_area"])
        if total_bua > 0:
            confirmed["int_walls_20cm_m"] = round(total_bua * 1.5, 2)
            sources["int_walls_20cm_m"] = "Geometric Fallback (BUA×1.5)"


    # Advanced CV Extractor & QS Heuristics Fallbacks
    
    # 1. Try to heal compound_length using CV first, then Math
    if not confirmed.get("compound_length") or confirmed.get("compound_length") == 0.0:
        cv_healed = False
        # Look for setting_out page to get CV perimeter
        for page_key, page in ext_res.items():
            if page.get("drawing_type") == "setting_out" or page.get("detected_type") == "setting_out":
                cv_perim = page.get("cv_perimeter_px", 0)
                cv_area = page.get("cv_area_px", 0)
                if cv_perim > 0 and cv_area > 0 and confirmed.get("plot_area"):
                    scale = math.sqrt(confirmed["plot_area"] / cv_area)
                    confirmed["compound_length"] = round(cv_perim * scale, 2)
                    confirmed["compound_length_is_estimated"] = True
                    sources["compound_length"] = "CV Heuristic (Est.)"
                    cv_healed = True
                    break
                    
        if not cv_healed:
            if confirmed.get("plot_area"):
                confirmed["compound_length"] = round(4 * math.sqrt(confirmed["plot_area"]), 2)
                confirmed["compound_length_is_estimated"] = True
                sources["compound_length"] = "Math Fallback (4√Area)"
            elif confirmed.get("gf_area"):
                confirmed["compound_length"] = round(4 * math.sqrt(confirmed["gf_area"] * 2), 2)
                confirmed["compound_length_is_estimated"] = True
                sources["compound_length"] = "Math Fallback (4√(GF*2))"

    # Ensure gf_area syncs back to floors["gf"]
    if confirmed.get("gf_area") and float(confirmed.get("gf_area")) > 0:
        if "gf" not in confirmed["floors"]:
            confirmed["floors"]["gf"] = {}
        if not confirmed["floors"]["gf"].get("area") or confirmed["floors"]["gf"].get("area") < 30.0:
            confirmed["floors"]["gf"]["area"] = confirmed["gf_area"]
            
    if confirmed.get("ext_perimeter") and float(confirmed.get("ext_perimeter")) > 0:
        if "gf" not in confirmed["floors"]:
            confirmed["floors"]["gf"] = {}
        if not confirmed["floors"]["gf"].get("ext_perimeter") or confirmed["floors"]["gf"].get("ext_perimeter") < 15.0:
            confirmed["floors"]["gf"]["ext_perimeter"] = confirmed["ext_perimeter"]

    if not confirmed.get("openings"):
        confirmed["openings"] = {"totals": {"door_count": 0, "window_area": 0.0}}
    
    # 2. Heal Doors using CV count first, then Math
    if confirmed["openings"]["totals"].get("door_count", 0) == 0:
        cv_doors = 0
        for page_key, page in ext_res.items():
            if page.get("detected_type") in ["ground_floor_plan", "first_floor_plan", "second_floor_plan"]:
                cv_doors += page.get("cv_door_count", 0)
        
        if cv_doors > 0:
            confirmed["openings"]["totals"]["door_count"] = cv_doors
            confirmed["openings"]["totals"]["door_count_is_estimated"] = True
            sources["door_count"] = "CV Count (Est.)"
        elif confirmed.get("gf_area"):
            confirmed["openings"]["totals"]["door_count"] = int(confirmed["gf_area"] / 25)
            confirmed["openings"]["totals"]["door_count_is_estimated"] = True
            sources["door_count"] = "Math Fallback (GF/25)"
            
    # 3. Heal Windows using CV count first, then Math
    if confirmed["openings"]["totals"].get("window_area", 0.0) == 0.0:
        cv_windows = 0
        for page_key, page in ext_res.items():
            if page.get("detected_type") in ["ground_floor_plan", "first_floor_plan", "second_floor_plan"]:
                cv_windows += page.get("cv_window_count", 0)
                
        if cv_windows > 0:
            # Assume 2.0m2 per window found by CV
            confirmed["openings"]["totals"]["window_area"] = float(cv_windows * 2.0)
            confirmed["openings"]["totals"]["window_area_is_estimated"] = True
            sources["window_area"] = "CV Count × 2.0m²"
        elif confirmed.get("gf_area"):
            # Assume windows are ~8% of floor area
            confirmed["openings"]["totals"]["window_area"] = float(confirmed["gf_area"] * 0.08)
            confirmed["openings"]["totals"]["window_area_is_estimated"] = True
            sources["window_area"] = "Math Fallback (8% of GF Area)"

    # 4. Fill in default editable assumptions if not present
    if "excavation_depth" not in confirmed:
        confirmed["excavation_depth"] = 1.25
        sources["excavation_depth"] = "Eng. Standard (Default)"
    elif "excavation_depth" not in sources:
        sources["excavation_depth"] = "Eng. Standard (Default)"
        
    if "neck_column_height" not in confirmed:
        confirmed["neck_column_height"] = 1.0
        sources["neck_column_height"] = "Eng. Standard (Default)"
    elif "neck_column_height" not in sources:
        sources["neck_column_height"] = "Eng. Standard (Default)"
        
    if "staircase_volume_per_level" not in confirmed:
        confirmed["staircase_volume_per_level"] = 5.2
        sources["staircase_volume_per_level"] = "Eng. Standard (Default)"
    elif "staircase_volume_per_level" not in sources:
        sources["staircase_volume_per_level"] = "Eng. Standard (Default)"
        
    if "solid_block_height" not in confirmed:
        confirmed["solid_block_height"] = 1.0
        sources["solid_block_height"] = "Eng. Standard (Default)"
    elif "solid_block_height" not in sources:
        sources["solid_block_height"] = "Eng. Standard (Default)"
            
    # Column Fallback
    if "column_schedule" not in confirmed.get("schedules", {}) or not confirmed["schedules"]["column_schedule"].get("columns"):
        gf_area = float(confirmed.get("gf_area") or 0.0)
        if gf_area > 0:
            est_count = max(4, int(gf_area / 16.0)) # Typical: 1 column per 16m2
            if "schedules" not in confirmed:
                confirmed["schedules"] = {}
            confirmed["schedules"]["column_schedule"] = {
                "columns": [
                    {"mark": "C1", "width_m": 0.2, "length_m": 0.6, "count": est_count, "count_in_plans": est_count}
                ]
            }
            sources["column_schedule"] = "Geometric Fallback"
            
    confirmed["sources"] = sources
    state_data["confirmed_auto_data"] = confirmed

@router.post("/confirm")
async def confirm_data(req: ConfirmDataReq, current_user: dict = Depends(get_current_user)):
    df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], req.project_id))
    if df_state.empty:
        raise HTTPException(status_code=400, detail="No active project.")
        
    state_data = json.loads(df_state.iloc[0]["state_data"])
    
    confirmed = req.confirmed_data
    # Clear is_estimated flags since they are confirmed/verified
    confirmed["compound_length_is_estimated"] = False
    if "openings" in confirmed and "totals" in confirmed["openings"]:
        confirmed["openings"]["totals"]["door_count_is_estimated"] = False
        confirmed["openings"]["totals"]["window_area_is_estimated"] = False
        
    # Mark edited fields as User Verified
    sources = confirmed.get("sources") or {}
    for k in ["longest_length", "longest_width", "plot_area", "gf_area", "ext_perimeter", "total_villa_height", "roof_perimeter", "roof_slab_area", "compound_length", "excavation_depth", "neck_column_height", "solid_block_height", "staircase_volume_per_level", "int_walls_10cm_m", "int_walls_20cm_m"]:
        if k in confirmed:
            sources[k] = "User Verified"
    if "openings" in confirmed and "totals" in confirmed["openings"]:
        sources["door_count"] = "User Verified"
        sources["window_area"] = "User Verified"
    confirmed["sources"] = sources
    
    state_data["confirmed_auto_data"] = confirmed
    
    # Heal and reconstruct missing fields from extraction_results
    reconstruct_project_inputs(state_data)
    
    state_data["current_step"] = 5
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    safe_execute(
        "UPDATE qto_active_projects SET current_step=5, state_data=%s WHERE user_id=%s AND project_id=%s",
        (state_json, current_user["id"], req.project_id)
    )
    return {"message": "Data confirmation saved."}
