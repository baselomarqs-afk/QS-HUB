import os
import json
import re
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import numpy as np
from PIL import Image

from api.auth import get_current_user
from utils.db import safe_query, safe_execute
from workflow.step3_extract import extract_page, merge_schedule_json_to_results
from engine.sanity_checker import sanity_check
from api.routers.data_review import reconstruct_project_inputs

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_settings.json")
def get_user_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

router = APIRouter()

CACHE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_qto_cache")
os.makedirs(CACHE_ROOT, exist_ok=True)

class RunExtractionReq(BaseModel):
    project_id: int

from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.responses import StreamingResponse
import asyncio

@router.post("/extract")
async def run_extraction(req: RunExtractionReq, current_user: dict = Depends(get_current_user)):
    df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], req.project_id))
    if df_state.empty:
        raise HTTPException(status_code=400, detail="No active project.")
        
    state_data = json.loads(df_state.iloc[0]["state_data"])
    classified = state_data.get("classified_pages") or []
    
    ready = [p for p in classified if p.get("detected_type") and p["detected_type"] != "unknown"]
    if not ready:
        raise HTTPException(status_code=400, detail="No pages classified for extraction. Please classify drawings first.")
        
    project_cache = os.path.join(CACHE_ROOT, str(req.project_id))
    
    str_texts = state_data.get("str_texts") or []
    arch_texts = state_data.get("arch_texts") or []
    custom_settings = get_user_settings()

    from engine.advanced_cv_extractor import process_floor_plan_image

    def get_pages_to_retry_from_warnings(warns: List[str]) -> Dict[str, List[str]]:
        retry_map = {}
        for w in warns:
            lw = w.lower()
            if "plot_area" in lw: retry_map.setdefault("setting_out", []).append(w)
            if "gf_area" in lw or "external_perimeter" in lw or "total_villa_height" in lw:
                retry_map.setdefault("ground_floor_plan", []).append(w)
            if "footing" in lw or "foundation" in lw: retry_map.setdefault("foundations", []).append(w)
            if "tb " in lw or "tie beam" in lw or "tie_beam" in lw: retry_map.setdefault("tie_beam", []).append(w)
            if "column" in lw:
                retry_map.setdefault("column_schedule", []).append(w)
                retry_map.setdefault("upper_columns", []).append(w)
                retry_map.setdefault("ground_columns", []).append(w)
            if "slab_1st" in lw: retry_map.setdefault("slab_1st", []).append(w)
            if "slab_2nd" in lw: retry_map.setdefault("slab_2nd", []).append(w)
            if "roof_slab" in lw: retry_map.setdefault("roof_slab", []).append(w)
            if "door" in lw or "window" in lw:
                retry_map.setdefault("door_schedule", []).append(w)
                retry_map.setdefault("window_schedule", []).append(w)
                retry_map.setdefault("schedules", []).append(w)
        return retry_map

    def extract_single_page(args):
        page_info, previous_warnings = args
        dtype = page_info["detected_type"]
        pdf_type = page_info["pdf"]
        page_idx = page_info["page_index"]
        page_num = page_info["page_num"]
        
        prefix = "str" if pdf_type == "structural" else "arch"
        img_path = os.path.join(project_cache, f"{prefix}_page_{page_idx}.png")
        
        if not os.path.exists(img_path):
            return None
            
        texts_src = str_texts if pdf_type == "structural" else arch_texts
        page_text = texts_src[page_idx] if page_idx < len(texts_src) else ""
        
        try:
            # Bypassing Numpy/PIL to prevent RAM exhaustion and thrashing
            extracted = extract_page(None, dtype, page_text, current_user["id"], previous_warnings, image_path=img_path)
            
            if dtype in ["ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan", "setting_out"]:
                cv_data = process_floor_plan_image(img_path)
                perim_m = extracted.get("ext_perimeter")
                if not perim_m:
                    l = extracted.get("overall_length_m", 0) or 0
                    w = extracted.get("overall_width_m", 0) or 0
                    perim_m = (l + w) * 2
                
                cv_perim_px = cv_data.get("cv_perimeter_px", 0)
                if perim_m and cv_perim_px > 0:
                    scale = perim_m / cv_perim_px
                    # Do not overwrite int_walls_length with the highly inflated cv_data value.
                    # The AI mathematically calculates it much more accurately from room dimensions.
                        
                extracted.update(cv_data)

            key = f"{pdf_type}_p{page_num}_{dtype}"
            return key, {**extracted, **page_info}
        except Exception as e:
            key = f"{pdf_type}_p{page_num}_{dtype}"
            return key, {
                "_ok": False,
                "_error": str(e),
                "drawing_type": dtype,
                **page_info
            }

    def event_generator():
        results = {}
        total_pages = len(ready)
        
        yield f'data: {json.dumps({"progress": 5, "status": f"Starting extraction for {total_pages} pages..."})}\n\n'
        
        # Pass 1: Extract all ready pages
        initial_args = [(p, None) for p in ready]
        completed_count = 0
        
        # Prevent Out-Of-Memory (OOM) crashes by limiting concurrent image processing
        # CRITICAL: Do NOT increase max_workers > 2 on Render Free Tier (512MB RAM). It causes silent OS thread kills.
        with ThreadPoolExecutor(max_workers=2) as executor:
            import concurrent.futures
            future_to_args = {executor.submit(extract_single_page, arg): arg for arg in initial_args}
            
            while future_to_args:
                done, not_done = concurrent.futures.wait(
                    future_to_args.keys(), 
                    timeout=15.0, 
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                if not done:
                    # Timeout reached without any task finishing -> send keep-alive to prevent Render 100s timeout
                    progress = 5 + int(70 * (completed_count / total_pages))
                    yield f'data: {json.dumps({"progress": progress, "status": f"Extracting AI Data ({completed_count}/{total_pages}) - Please wait..."})}\n\n'
                    continue
                    
                for future in done:
                    arg = future_to_args.pop(future)
                    completed_count += 1
                    try:
                        item = future.result()
                        if item:
                            key, val = item
                            results[key] = val
                    except Exception as exc:
                        print(f"Extraction generated an exception: {exc}")
                    
                    # Report progress up to 75% for Phase 1
                    progress = 5 + int(70 * (completed_count / total_pages))
                    yield f'data: {json.dumps({"progress": progress, "status": f"Extracting AI Data ({completed_count}/{total_pages})..."})}\n\n'
                
        yield f'data: {json.dumps({"progress": 80, "status": "Cross-checking doors and windows..."})}\n\n'
        
        # Cross check counts
        plan_texts = []
        for p in ready:
            if p["pdf"] == "architectural" and p["detected_type"] in {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan"}:
                idx = p["page_index"]
                if idx < len(arch_texts):
                    plan_texts.append(arch_texts[idx].upper())
                    
        if plan_texts:
            full_text = " \n ".join(plan_texts)
            for k, data in results.items():
                if data.get("drawing_type") in {"schedules", "door_schedule", "window_schedule"}:
                    for lst_type in ["doors", "windows"]:
                        for item in data.get(lst_type, []):
                            mark = str(item.get("mark", "")).strip().upper()
                            if mark and len(mark) > 1:
                                from _pdf_utils import normalize_mark
                                m_clean = normalize_mark(mark)
                                match_pattern = "".join(c + r"[\s\-_./]*" if c.isalpha() else c for c in m_clean).rstrip(r"[\s\-_./]*")
                                n = len(re.findall(rf"\b{match_pattern}\b", full_text))
                                if n > 0:
                                    item["count_in_plans"] = n
                                    item["count_source"] = "floor_plans_fitz"
                                    
        state_data["extraction_results"] = results
        state_data["current_step"] = 4
        
        yield f'data: {json.dumps({"progress": 85, "status": "Running sanity checks..."})}\n\n'
        
        reconstruct_project_inputs(state_data)
        confirmed = state_data.get("confirmed_auto_data") or {}
        warnings = sanity_check(confirmed, custom_settings)
        
        # Auto-rectify loop
        if warnings:
            yield f'data: {json.dumps({"progress": 90, "status": "Auto-rectifying errors found in checks..."})}\n\n'
            retry_map = get_pages_to_retry_from_warnings(warnings)
            retry_args = []
            for p in ready:
                dtype = p["detected_type"]
                if dtype in retry_map:
                    retry_args.append((p, retry_map[dtype]))
            
            if retry_args:
                retry_count = 0
                total_retries = len(retry_args)
                # CRITICAL: Do NOT increase max_workers > 1 on Render Free Tier (512MB RAM). It causes silent OS thread kills.
                with ThreadPoolExecutor(max_workers=1) as executor:
                    import concurrent.futures
                    future_to_args = {executor.submit(extract_single_page, arg): arg for arg in retry_args}
                    
                    while future_to_args:
                        done, not_done = concurrent.futures.wait(
                            future_to_args.keys(), 
                            timeout=15.0, 
                            return_when=concurrent.futures.FIRST_COMPLETED
                        )
                        
                        if not done:
                            prog = 90 + int(8 * (retry_count / total_retries))
                            yield f'data: {json.dumps({"progress": prog, "status": f"Re-analyzing {retry_count}/{total_retries} pages - Please wait..."})}\n\n'
                            continue
                            
                        for future in done:
                            arg = future_to_args.pop(future)
                            retry_count += 1
                            try:
                                item = future.result()
                                if item:
                                    key, val = item
                                    results[key] = val
                            except Exception:
                                pass
                            prog = 90 + int(8 * (retry_count / total_retries))
                            yield f'data: {json.dumps({"progress": prog, "status": f"Re-analyzing {retry_count}/{total_retries} pages..."})}\n\n'
                        
                state_data["extraction_results"] = results
                reconstruct_project_inputs(state_data)
                confirmed = state_data.get("confirmed_auto_data") or {}
                warnings = sanity_check(confirmed, custom_settings)

        yield f'data: {json.dumps({"progress": 99, "status": "Saving extraction results..."})}\n\n'
        
        state_data["sanity_warnings"] = warnings
        state_json = json.dumps(state_data, ensure_ascii=False, default=str)
        safe_execute(
            "UPDATE qto_active_projects SET current_step=4, state_data=%s WHERE user_id=%s AND project_id=%s",
            (state_json, current_user["id"], req.project_id)
        )
        
        final_payload = {
            "done": True,
            "extraction_results": results,
            "sanity_warnings": warnings,
            "next_step": 4
        }
        yield f'data: {json.dumps(final_payload)}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")
