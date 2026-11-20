"""Background worker entrypoint for queued SaaS jobs.

Polls qto_background_jobs for queued work and executes it outside the
request/response cycle so the API never blocks on long-running AI calls.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import threading
import time
import traceback

from utils.jobs import (
    get_job,
    mark_job_done,
    mark_job_failed,
    mark_job_started,
    next_job,
    update_job_progress,
)

_log = logging.getLogger("qto.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# Dedicated bounded background pool (max 2 concurrent jobs protects 512MB RAM hosts
# while keeping FastAPI's HTTP event loop 100% responsive for all other users).
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="qto-worker")
_PROGRESS_LOCK = threading.Lock()
_LIVE_PROGRESS: dict[int, dict] = {}


# ── Job Processors ────────────────────────────────────────────────

def _process_pdf_extraction(payload: dict) -> dict:
    """Extract text + render page images from an uploaded PDF."""
    from pdf_engine.pdf_loader import load_pdf_pages, extract_page_text, page_to_pil
    from PIL import Image
    import os

    project_id = payload["project_id"]
    user_id = payload["user_id"]
    file_path = payload["file_path"]
    prefix = payload.get("prefix", "str")
    cache_dir = payload.get("cache_dir", f"_qto_cache/{project_id}")

    os.makedirs(cache_dir, exist_ok=True)

    with open(file_path, "rb") as f:
        content = f.read()

    pages = load_pdf_pages(content)
    texts = extract_page_text(content)

    for idx, page_arr in enumerate(pages):
        pil_img = page_to_pil(page_arr)
        w, h = pil_img.size
        if max(w, h) > 1600:
            scale = 1600 / max(w, h)
            pil_img = pil_img.resize((int(w * scale), int(h * scale)))
        pil_img.save(os.path.join(cache_dir, f"{prefix}_page_{idx}.png"), format="PNG")

    return {
        "page_count": len(pages),
        "texts": texts,
        "prefix": prefix,
        "project_id": project_id,
    }


def _process_ai_extraction(payload: dict) -> dict:
    """Run Gemini Vision AI extraction on a single classified page."""
    from PIL import Image
    import numpy as np
    from workflow.step3_extract import extract_page
    from engine.advanced_cv_extractor import process_floor_plan_image

    img_path = payload["img_path"]
    dtype = payload["detected_type"]
    page_text = payload.get("page_text", "")
    user_id = payload["user_id"]

    pil_img = Image.open(img_path)
    page_arr = np.array(pil_img)[:, :, ::-1].copy()

    try:
        import os, json
        # img_path is like _qto_cache/PROJ/arch_page_1.png
        cache_dir = os.path.dirname(img_path)
        filename = os.path.basename(img_path)
        # extract prefix and page index from filename (e.g. arch_page_1.png)
        parts = filename.split("_")
        prefix = parts[0]
        page_idx = int(parts[2].split(".")[0])
        
        state_path = os.path.join(cache_dir, "state_data.json")
        original_pdf_path = None
        internal_page_idx = page_idx
        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                state_data = json.load(f)
            boundaries = state_data.get(f"{prefix}_boundaries", [])
            for b in boundaries:
                if b["start"] <= page_idx <= b["end"]:
                    original_pdf_path = os.path.join(cache_dir, b["pdf_path"])
                    internal_page_idx = page_idx - b["start"]
                    break

        extracted = extract_page(page_arr, dtype, page_text, user_id, pdf_path=original_pdf_path, internal_page_idx=internal_page_idx)
    except Exception as e:
        _log.exception("Worker AI extraction failed")
        extracted = {"_ok": False, "_error": str(e), "drawing_type": dtype}

    # Apply CV extraction for floor plans
    cv_types = {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan", "setting_out"}
    if dtype in cv_types:
        try:
            cv_data = process_floor_plan_image(img_path)
            perim_m = extracted.get("ext_perimeter") or 0.0
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
                    extracted["_ok"] = True
                    
            extracted.update(cv_data)
        except Exception as cve:
            _log.exception("OpenCV failed: %s", cve)

    return extracted


def _process_full_pipeline(payload: dict) -> dict:
    """Run the entire classify → extract → calculate pipeline for a project.
    
    This is the heavy job that was previously blocking inside the API request.
    """
    from PIL import Image
    import numpy as np
    from workflow.step2_classify import _classify_single, _ai_classify
    from workflow.step3_extract import extract_page
    from engine.advanced_cv_extractor import process_floor_plan_image
    from pdf_engine.smart_classifier import PAGE_ITEMS_MAP
    import os

    project_id = payload["project_id"]
    user_id = payload["user_id"]
    cache_dir = payload.get("cache_dir", f"_qto_cache/{project_id}")
    classified_pages = payload.get("classified_pages", [])

    results = {}
    for page_info in classified_pages:
        dtype = page_info.get("detected_type")
        if not dtype or dtype == "unknown":
            continue

        prefix = "str" if page_info["pdf"] == "structural" else "arch"
        img_path = os.path.join(cache_dir, f"{prefix}_page_{page_info['page_index']}.png")
        if not os.path.exists(img_path):
            continue

        try:
            pil_img = Image.open(img_path)
            page_arr = np.array(pil_img)[:, :, ::-1].copy()
            page_text = page_info.get("page_text", "")

            try:
                state_path = os.path.join(cache_dir, "state_data.json")
                original_pdf_path = None
                internal_page_idx = page_info['page_index']
                if os.path.exists(state_path):
                    with open(state_path, "r") as f:
                        state_data = json.load(f)
                    boundaries = state_data.get(f"{page_info['pdf']}_boundaries", [])
                    for b in boundaries:
                        if b["start"] <= page_info['page_index'] <= b["end"]:
                            original_pdf_path = os.path.join(cache_dir, b["pdf_path"])
                            internal_page_idx = page_info['page_index'] - b["start"]
                            break
                            
                extracted = extract_page(page_arr, dtype, page_text, user_id, pdf_path=original_pdf_path, internal_page_idx=internal_page_idx)
            except Exception as e:
                _log.exception("Worker AI extraction failed for page %s", page_info.get("page_num"))
                extracted = {"_ok": False, "_error": str(e), "drawing_type": dtype}

            cv_types = {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan", "setting_out"}
            if dtype in cv_types:
                try:
                    cv_data = process_floor_plan_image(img_path)
                    perim_m = extracted.get("ext_perimeter") or 0.0
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
                            # Resurrect the page if AI failed but OpenCV succeeded!
                            extracted["_ok"] = True
                            
                    extracted.update(cv_data)
                except Exception as cve:
                    _log.exception("OpenCV failed: %s", cve)

            key = f"{page_info['pdf']}_p{page_info['page_num']}_{dtype}"
            results[key] = {**extracted, **page_info}

        except Exception as outer_e:
            _log.exception("Worker image processing failed for page %s", page_info.get("page_num"))
            key = f"{page_info['pdf']}_p{page_info['page_num']}_{dtype}"
            results[key] = {"_ok": False, "_error": str(outer_e), "drawing_type": dtype, **page_info}

    return {"extraction_results": results}


def _process_project_extraction(payload: dict, progress_cb=None) -> dict:
    """Run full Step 3 AI + OpenCV + vector extraction for an active project."""
    from api.routers.extraction import execute_project_extraction
    project_id = int(payload["project_id"])
    user_id = int(payload["user_id"])
    return execute_project_extraction(project_id, user_id, progress_cb=progress_cb)


# ── Dispatcher ────────────────────────────────────────────────────

_PROCESSORS = {
    "pdf_extraction": _process_pdf_extraction,
    "ai_extraction": _process_ai_extraction,
    "full_pipeline": _process_full_pipeline,
    "project_extraction": _process_project_extraction,
}


def process_job(job: dict, progress_cb=None) -> dict:
    job_type = job["job_type"]
    processor = _PROCESSORS.get(job_type)
    if not processor:
        raise ValueError(f"No processor registered for job_type='{job_type}'")

    payload = job.get("payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    payload = payload or {}

    _log.info("Processing job #%s type=%s", job["id"], job_type)
    if job_type == "project_extraction":
        result = processor(payload, progress_cb=progress_cb)
    else:
        result = processor(payload)
    _log.info("Completed job #%s type=%s", job["id"], job_type)
    return result


def _run_job_by_id(job_id: int) -> None:
    """Execute a queued job inside the background thread pool without blocking HTTP."""
    job = get_job(job_id)
    if not job:
        _log.warning("Background job #%d not found", job_id)
        return
    mark_job_started(job_id)

    def _on_progress(progress: int, status_text: str) -> None:
        with _PROGRESS_LOCK:
            _LIVE_PROGRESS[job_id] = {
                "progress": int(progress),
                "status_text": str(status_text),
            }
        try:
            update_job_progress(job_id, int(progress), str(status_text))
        except Exception:
            pass

    _on_progress(5, "Starting background extraction worker...")
    try:
        result = process_job(job, progress_cb=_on_progress)
        mark_job_done(job_id, result)
        with _PROGRESS_LOCK:
            _LIVE_PROGRESS[job_id] = {"progress": 100, "status_text": "Completed"}
    except Exception as exc:
        _log.exception("Background job #%d failed", job_id)
        err_msg = str(exc) or traceback.format_exc()
        mark_job_failed(job_id, err_msg)
        with _PROGRESS_LOCK:
            _LIVE_PROGRESS.pop(job_id, None)


def submit_background_job(job_id: int) -> None:
    """Dispatch an already-enqueued job to the worker thread pool immediately."""
    with _PROGRESS_LOCK:
        _LIVE_PROGRESS[job_id] = {"progress": 2, "status_text": "Queued for extraction worker..."}
    _EXECUTOR.submit(_run_job_by_id, int(job_id))


def get_job_status(job_id: int, user_id: int, role: str = "user") -> dict | None:
    """Return ownership-verified job status, live progress, and final result."""
    job = get_job(job_id)
    if not job:
        return None
    if role != "admin" and int(job.get("user_id") or 0) != int(user_id):
        return {"_forbidden": True}

    status = str(job.get("status") or "queued")
    raw_res = job.get("result")
    parsed_res = None
    if raw_res:
        try:
            parsed_res = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
        except Exception:
            parsed_res = None

    with _PROGRESS_LOCK:
        live = _LIVE_PROGRESS.get(job_id)

    if status == "done":
        return {
            "job_id": int(job_id),
            "status": "done",
            "progress": 100,
            "status_text": "Completed",
            "result": parsed_res or {},
            "error": None,
        }
    if status == "failed":
        return {
            "job_id": int(job_id),
            "status": "failed",
            "progress": 0,
            "status_text": "Extraction failed",
            "result": None,
            "error": str(job.get("error") or "Extraction job failed."),
        }

    # Queued or running
    prog = live["progress"] if live else (parsed_res.get("progress", 5) if isinstance(parsed_res, dict) else 5)
    st_txt = live["status_text"] if live else (
        parsed_res.get("status_text", "Working in background...") if isinstance(parsed_res, dict) else "Working in background..."
    )
    return {
        "job_id": int(job_id),
        "status": status,
        "progress": int(prog),
        "status_text": str(st_txt),
        "result": None,
        "error": None,
    }


def run_forever(poll_seconds: int = 5) -> None:
    _log.info("Worker started — polling every %ds", poll_seconds)
    while True:
        job = next_job()
        if not job:
            time.sleep(poll_seconds)
            continue
        job_id = int(job["id"])
        _run_job_by_id(job_id)


if __name__ == "__main__":
    run_forever()
