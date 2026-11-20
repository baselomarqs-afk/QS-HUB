import os
import json
import re
import asyncio
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
from utils.garbage_collection import background_cleanup_project
from _pdf_utils import normalize_mark

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
_CLEANUP_TASKS: Dict[int, asyncio.Task] = {}

class RunExtractionReq(BaseModel):
    project_id: int

from concurrent.futures import ThreadPoolExecutor
from fastapi.responses import StreamingResponse
import asyncio
import concurrent.futures


def execute_project_extraction(project_id: int, user_id: int, progress_cb=None) -> Dict[str, Any]:
    """Run the complete Step 3 AI + OpenCV + vector extraction pipeline synchronously
    inside a worker thread (NEVER on the FastAPI asyncio event loop).

    `progress_cb(progress: int, status_text: str)` is called at each milestone so both
    background-job polling (`worker.py`) and SSE streaming get live updates.
    """
    def _emit(prog: int, msg: str) -> None:
        if progress_cb:
            try:
                progress_cb(int(prog), str(msg))
            except Exception:
                pass

    df_state = safe_query(
        "SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s",
        (user_id, project_id),
    )
    if df_state.empty:
        raise ValueError("No active project.")

    state_data = json.loads(df_state.iloc[0]["state_data"])
    classified = state_data.get("classified_pages") or []

    ready = [p for p in classified if p.get("detected_type") and p["detected_type"] != "unknown"]
    if not ready:
        raise ValueError("No pages classified for extraction. Please classify drawings first.")

    project_cache = os.path.join(CACHE_ROOT, str(project_id))

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

    def _resolve_pdf_page(prefix: str, p_idx: int):
        boundaries = state_data.get(f"{prefix}_boundaries", [])
        for b in boundaries:
            if b["start"] <= p_idx <= b["end"]:
                return os.path.join(project_cache, b["pdf_path"]), p_idx - b["start"]
        return None, p_idx

    def _read_full_pdf_page_text(pdf_path: str, internal_idx: int, fallback_text: str = "") -> str:
        if pdf_path and os.path.exists(pdf_path):
            try:
                import fitz
                with fitz.open(pdf_path) as doc:
                    if 0 <= internal_idx < len(doc):
                        txt = doc[internal_idx].get_text("text")
                        if txt and txt.strip():
                            return txt
            except Exception:
                pass
        return fallback_text

    def extract_single_page(args):
        page_info, previous_warnings = args
        dtype = page_info["detected_type"]
        pdf_type = page_info["pdf"]
        page_idx = page_info["page_index"]
        page_num = page_info["page_num"]

        prefix = "str" if pdf_type == "structural" else "arch"
        img_path = os.path.join(project_cache, f"{prefix}_page_{page_idx}.jpg")
        if not os.path.exists(img_path):
            img_path = os.path.join(project_cache, f"{prefix}_page_{page_idx}.jpeg")
        if not os.path.exists(img_path):
            img_path = os.path.join(project_cache, f"{prefix}_page_{page_idx}.png")

        if not os.path.exists(img_path):
            return None

        texts_src = str_texts if pdf_type == "structural" else arch_texts
        fallback_text = texts_src[page_idx] if page_idx < len(texts_src) else ""

        original_pdf_path, internal_page_idx = _resolve_pdf_page(prefix, page_idx)
        page_text = _read_full_pdf_page_text(original_pdf_path, internal_page_idx, fallback_text)

        try:
            extracted = extract_page(
                None,
                dtype,
                page_text,
                user_id,
                previous_warnings,
                image_path=img_path,
                pdf_path=original_pdf_path,
                internal_page_idx=internal_page_idx,
            )

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
                    cv_data["cv_perimeter_m"] = cv_perim_px * scale
                    cv_data["cv_area_m2"] = cv_data.get("cv_area_px", 0) * (scale ** 2)

                    if not extracted.get("total_floor_area") or extracted.get("total_floor_area", 0) == 0:
                        extracted["total_floor_area"] = round(cv_data["cv_area_m2"], 2)
                        extracted["notes"] = extracted.get("notes", "") + f" [OPENCV FALLBACK: Area calculated geometrically as {extracted['total_floor_area']}m2]"

                extracted.update(cv_data)

            if dtype in ["elevations", "ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan"]:
                if not extracted.get("floor_height") and not extracted.get("floor_to_floor_heights_m") and not extracted.get("gf_height_m"):
                    raw_matches = re.findall(
                        r'(?:F\.?F\.?L\.?|S\.?S\.?L\.?|T\.?O\.?S\.?|LVL|LEVEL|PARAPET\s+LEV\w*)[\s.:=]*\+?\s*(\d+\.\d{1,2})',
                        page_text,
                        re.IGNORECASE,
                    )
                    if raw_matches:
                        heights = sorted({round(float(m), 2) for m in raw_matches})
                        if len(heights) > 1:
                            floor_lvls = [h for h in heights if h >= 0.15]
                            diffs = []
                            for a, b in zip(floor_lvls, floor_lvls[1:]):
                                d = round(b - a, 2)
                                if 2.5 <= d <= 6.0:
                                    diffs.append(d)
                            if diffs:
                                mode_h = max(set(diffs), key=diffs.count)
                                extracted["floor_height"] = mode_h
                                extracted["notes"] = extracted.get("notes", "") + f" [LEVEL MARKER FALLBACK: Floor height derived as {mode_h}m]"
                                if dtype == "elevations":
                                    extracted["floor_to_floor_heights_m"] = diffs
                                    extracted["gf_height_m"] = diffs[0]
                                    if len(diffs) >= 2:
                                        extracted["f1_height_m"] = diffs[1]
                                    if len(diffs) >= 3:
                                        extracted["f2_height_m"] = diffs[2]
                                    last_diff = round(floor_lvls[-1] - floor_lvls[-2], 2)
                                    if 0.6 <= last_diff <= 2.2 and not extracted.get("parapet_height_m"):
                                        extracted["parapet_height_m"] = last_diff
                                    if not extracted.get("total_villa_height_m"):
                                        extracted["total_villa_height_m"] = round(sum(diffs), 2)

            key = f"{pdf_type}_p{page_num}_{dtype}"
            return key, {**extracted, **page_info}
        except Exception as e:
            key = f"{pdf_type}_p{page_num}_{dtype}"
            return key, {
                "_ok": False,
                "_error": str(e),
                "drawing_type": dtype,
                **page_info,
            }

    results = {}
    total_pages = len(ready)
    _emit(5, f"Starting extraction for {total_pages} pages...")

    initial_args = [(p, None) for p in ready]
    completed_count = 0

    from utils.key_manager import get_key_manager
    _page_workers = 2 if get_key_manager().key_count() >= 4 else 1
    with ThreadPoolExecutor(max_workers=_page_workers) as executor:
        future_to_args = {executor.submit(extract_single_page, arg): arg for arg in initial_args}
        while future_to_args:
            done, _ = concurrent.futures.wait(
                future_to_args.keys(),
                timeout=15.0,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if not done:
                progress = 5 + int(70 * (completed_count / total_pages))
                _emit(progress, f"Extracting AI Data ({completed_count}/{total_pages}) - Please wait...")
                continue

            for future in done:
                future_to_args.pop(future)
                completed_count += 1
                try:
                    item = future.result()
                    if item:
                        key, val = item
                        results[key] = val
                except Exception as exc:
                    print(f"Extraction generated an exception: {exc}")

                progress = 5 + int(70 * (completed_count / total_pages))
                _emit(progress, f"Extracting AI Data ({completed_count}/{total_pages})...")

    _emit(80, "Cross-checking doors and windows...")

    plan_texts = []
    for p in ready:
        if p["pdf"] == "architectural" and p["detected_type"] in {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan"}:
            idx = p["page_index"]
            fallback_t = arch_texts[idx] if idx < len(arch_texts) else ""
            arch_pdf_path, arch_internal_idx = _resolve_pdf_page("arch", idx)
            full_page_t = _read_full_pdf_page_text(arch_pdf_path, arch_internal_idx, fallback_t)
            if full_page_t:
                plan_texts.append(full_page_t.upper())

    if plan_texts:
        full_text = " \n ".join(plan_texts)
        for k, data in results.items():
            if data.get("drawing_type") in {"schedules", "door_schedule", "window_schedule"}:
                for lst_type in ["doors", "windows"]:
                    for item in data.get(lst_type, []):
                        mark = str(item.get("mark", "")).strip().upper()
                        if mark and len(mark) > 1:
                            m_clean = normalize_mark(mark)
                            match_pattern = "".join(c + r"[\s\-_./]*" if c.isalpha() else c for c in m_clean).rstrip(r"[\s\-_./]*")
                            n = len(re.findall(rf"\b{match_pattern}\b", full_text))
                            if n > 0:
                                item["count_in_plans"] = n
                                item["count_source"] = "floor_plans_fitz"

    _PERFLOOR_COL_DTYPES = {
        "neck_columns", "ground_columns", "columns_1f",
        "columns_2f", "columns_roof", "column_layout",
    }
    try:
        import fitz as _fitz
        for k, data in results.items():
            dtype = data.get("drawing_type") or data.get("detected_type")
            if dtype not in _PERFLOOR_COL_DTYPES:
                continue
            cols = data.get("columns") or []
            if not cols:
                continue
            pdf_idx = data.get("page_index")
            if pdf_idx is None:
                continue
            str_pdf_path, internal_idx = _resolve_pdf_page("str", int(pdf_idx))
            if not (str_pdf_path and os.path.exists(str_pdf_path)):
                continue
            known_marks = {str(c.get("mark", "")).strip().upper(): c for c in cols if c.get("mark")}
            if not known_marks:
                continue
            with _fitz.open(str_pdf_path) as _doc:
                if internal_idx >= len(_doc):
                    continue
                _pg = _doc[internal_idx]
                _ph = _pg.rect.height
                plan_counts = {}
                total_counts = {}
                for _w in _pg.get_text("words"):
                    tok = _w[4].strip().rstrip("*#").upper()
                    if tok in known_marks:
                        total_counts[tok] = total_counts.get(tok, 0) + 1
                        yc = (_w[1] + _w[3]) / 2.0
                        if yc < _ph * 0.74:
                            plan_counts[tok] = plan_counts.get(tok, 0) + 1
                use_counts = plan_counts if sum(plan_counts.values()) >= 3 else {
                    mk: max(1, cnt - 1) if cnt > 1 else cnt for mk, cnt in total_counts.items()
                }
                if sum(use_counts.values()) >= 3:
                    for mk, c_obj in known_marks.items():
                        if mk in use_counts and use_counts[mk] > 0:
                            c_obj["count"] = use_counts[mk]
                            c_obj["count_source"] = "column_layout_fitz"
    except Exception as _ce:
        print(f"Error counting per-floor columns with PyMuPDF: {_ce}")

    col_layout_pages = [
        p for p in ready
        if p["pdf"] == "structural" and p["detected_type"] == "column_layout"
    ]
    if col_layout_pages:
        from _pdf_utils import count_token_in_page
        for k, data in results.items():
            if data.get("drawing_type") == "upper_columns":
                all_marks = [str(c.get("mark", "")).strip().upper() for c in data.get("columns", []) if c.get("mark")]
                if all_marks:
                    for lp in col_layout_pages:
                        pdf_idx = lp["page_index"]
                        str_pdf_path, internal_idx = _resolve_pdf_page("str", pdf_idx)
                        if str_pdf_path and os.path.exists(str_pdf_path):
                            try:
                                counts = count_token_in_page(str_pdf_path, internal_idx, all_marks)
                                for c in data.get("columns", []):
                                    m = str(c.get("mark", "")).strip().upper()
                                    if m in counts and counts[m] > 0:
                                        c["count_gf"] = c.get("count_gf", 0) + counts[m]
                                        c["count_1f"] = c.get("count_1f", 0) + counts[m]
                                        if state_data.get("current_step") and state_data.get("confirmed_auto_data"):
                                            if "2f" in state_data.get("confirmed_auto_data", {}).get("floors", {}):
                                                c["count_2f"] = c.get("count_2f", 0) + counts[m]
                                        c["count_source"] = "column_layout_fitz"
                            except Exception as ex:
                                print(f"Error counting columns with PyMuPDF: {ex}")

    state_data["extraction_results"] = results
    state_data["current_step"] = 4

    try:
        from workflow.openings_counter import extract_openings_for_project
        vec_openings = extract_openings_for_project(
            project_cache,
            classified_pages=ready,
            arch_boundaries=state_data.get("arch_boundaries") or [],
        )
        if vec_openings and vec_openings.get("_ok"):
            state_data["_vector_openings"] = vec_openings
    except Exception as _ve:
        print(f"[openings_counter] skipped: {_ve}")

    try:
        from workflow.floor_classifier import classify_for_project
        ftypes = classify_for_project(project_cache)
        if ftypes:
            state_data["floor_types"] = {fk: v["type"] for fk, v in ftypes.items()}
    except Exception as _fe:
        print(f"[floor_classifier] skipped: {_fe}")

    _emit(85, "Running sanity checks...")

    reconstruct_project_inputs(state_data)
    confirmed = state_data.get("confirmed_auto_data") or {}
    warnings = sanity_check(confirmed, custom_settings)

    if warnings:
        _emit(90, "Auto-rectifying errors found in checks...")
        retry_map = get_pages_to_retry_from_warnings(warnings)
        retry_args = []
        for p in ready:
            dtype = p["detected_type"]
            if dtype in retry_map:
                retry_args.append((p, retry_map[dtype]))

        if retry_args:
            retry_count = 0
            total_retries = len(retry_args)
            with ThreadPoolExecutor(max_workers=_page_workers) as executor:
                future_to_args = {executor.submit(extract_single_page, arg): arg for arg in retry_args}
                while future_to_args:
                    done, _ = concurrent.futures.wait(
                        future_to_args.keys(),
                        timeout=15.0,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    if not done:
                        prog = 90 + int(8 * (retry_count / total_retries))
                        _emit(prog, f"Re-analyzing {retry_count}/{total_retries} pages - Please wait...")
                        continue
                    for future in done:
                        future_to_args.pop(future)
                        retry_count += 1
                        try:
                            item = future.result()
                            if item:
                                key, val = item
                                results[key] = val
                        except Exception:
                            pass
                        prog = 90 + int(8 * (retry_count / total_retries))
                        _emit(prog, f"Re-analyzing {retry_count}/{total_retries} pages...")

            state_data["extraction_results"] = results
            reconstruct_project_inputs(state_data)
            confirmed = state_data.get("confirmed_auto_data") or {}
            warnings = sanity_check(confirmed, custom_settings)

    _emit(99, "Saving extraction results...")

    state_data["sanity_warnings"] = warnings
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    safe_execute(
        "UPDATE qto_active_projects SET current_step=4, state_data=%s WHERE user_id=%s AND project_id=%s",
        (state_json, user_id, project_id),
    )

    return {
        "done": True,
        "extraction_results": results,
        "confirmed_auto_data": state_data.get("confirmed_auto_data") or {},
        "sanity_warnings": warnings,
        "next_step": 4,
    }


def _schedule_cache_cleanup(project_id: int) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    old_task = _CLEANUP_TASKS.pop(project_id, None)
    if old_task and not old_task.done():
        old_task.cancel()
    _cleanup_task = loop.create_task(
        background_cleanup_project(os.path.join(CACHE_ROOT, str(project_id)), delay_seconds=6 * 3600)
    )
    _CLEANUP_TASKS[project_id] = _cleanup_task
    _cleanup_task.add_done_callback(
        lambda t, pid=project_id: _CLEANUP_TASKS.pop(pid, None)
        if _CLEANUP_TASKS.get(pid) is t else None
    )


@router.post("/extract/start")
async def start_extraction_job(req: RunExtractionReq, current_user: dict = Depends(get_current_user)):
    """Enqueue extraction in qto_background_jobs and execute asynchronously via worker.py.
    Returns immediately (<50ms) so the API server NEVER freezes on large PDFs."""
    df_state = safe_query(
        "SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s",
        (current_user["id"], req.project_id),
    )
    if df_state.empty:
        raise HTTPException(status_code=400, detail="No active project.")

    state_data = json.loads(df_state.iloc[0]["state_data"])
    classified = state_data.get("classified_pages") or []
    ready = [p for p in classified if p.get("detected_type") and p["detected_type"] != "unknown"]
    if not ready:
        raise HTTPException(status_code=400, detail="No pages classified for extraction. Please classify drawings first.")

    from utils.jobs import enqueue_job
    import worker as bg_worker

    job_id = enqueue_job(
        "project_extraction",
        {"project_id": req.project_id, "user_id": current_user["id"]},
        user_id=current_user["id"],
        project_id=req.project_id,
    )
    if not job_id:
        raise HTTPException(status_code=500, detail="Failed to queue background extraction job.")

    bg_worker.submit_background_job(job_id)
    _schedule_cache_cleanup(req.project_id)
    return {"job_id": job_id, "status": "queued", "progress": 2}


@router.get("/extract/status/{job_id}")
async def get_extraction_job_status(job_id: int, current_user: dict = Depends(get_current_user)):
    """Poll status and live progress of an extraction job started via /extract/start."""
    import worker as bg_worker

    info = bg_worker.get_job_status(job_id, current_user["id"], current_user.get("role", "user"))
    if info is None:
        raise HTTPException(status_code=404, detail="Extraction job not found.")
    if info.get("_forbidden"):
        raise HTTPException(status_code=403, detail="Access denied.")
    return info


@router.post("/extract")
async def run_extraction(req: RunExtractionReq, current_user: dict = Depends(get_current_user)):
    """Legacy SSE extraction endpoint — now runs off the asyncio event loop via worker thread."""
    df_state = safe_query(
        "SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s",
        (current_user["id"], req.project_id),
    )
    if df_state.empty:
        raise HTTPException(status_code=400, detail="No active project.")

    state_data = json.loads(df_state.iloc[0]["state_data"])
    classified = state_data.get("classified_pages") or []
    ready = [p for p in classified if p.get("detected_type") and p["detected_type"] != "unknown"]
    if not ready:
        raise HTTPException(status_code=400, detail="No pages classified for extraction. Please classify drawings first.")

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _progress_cb(prog: int, msg: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"progress": prog, "status": msg})

    def _run_in_worker() -> None:
        try:
            payload = execute_project_extraction(req.project_id, current_user["id"], progress_cb=_progress_cb)
            loop.call_soon_threadsafe(queue.put_nowait, payload)
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, {"error": str(exc)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    import worker as bg_worker
    bg_worker._EXECUTOR.submit(_run_in_worker)
    _schedule_cache_cleanup(req.project_id)

    async def event_generator():
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                yield f'data: {json.dumps({"status": "Working in background..."})}\n\n'
                continue
            if item is None:
                break
            yield f'data: {json.dumps(item)}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")
