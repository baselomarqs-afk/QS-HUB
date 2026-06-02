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
            if page.get("total_doors_count"):
                openings["totals"]["door_count"] += int(page["total_doors_count"])
            if page.get("total_windows_area"):
                openings["totals"]["window_area"] += float(page["total_windows_area"])
                
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

    # Heal the building footprint dimensions from any page that carries them —
    # the foundation / setting-out pages usually report longest_length/width.
    # (Without this, excavation/backfill/road-base/anti-termite collapse to ~0.)
    for page_key, page in ext_res.items():
        if not isinstance(page, dict) or not page.get("_ok"):
            continue
        for field in ("longest_length", "longest_width", "total_villa_height"):
            if (not confirmed.get(field)) and page.get(field):
                confirmed[field] = page.get(field)

    for field in ["longest_length", "longest_width", "total_villa_height"]:
        if confirmed.get(field) and field not in sources:
            sources[field] = "AI OCR"
                
    # Advanced CV Extractor & QS Heuristics Fallbacks
    import math
    
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
    for k in ["longest_length", "longest_width", "plot_area", "gf_area", "ext_perimeter", "roof_perimeter", "roof_slab_area", "compound_length", "excavation_depth", "neck_column_height", "solid_block_height", "staircase_volume_per_level"]:
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
