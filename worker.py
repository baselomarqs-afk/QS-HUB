"""Background worker entrypoint for queued SaaS jobs.

Polls qto_background_jobs for queued work and executes it outside the
request/response cycle so the API never blocks on long-running AI calls.
"""
from __future__ import annotations

import json
import logging
import time
import traceback

from utils.jobs import mark_job_done, mark_job_failed, mark_job_started, next_job

_log = logging.getLogger("qto.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


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

    extracted = extract_page(page_arr, dtype, page_text, user_id)

    # Apply CV extraction for floor plans
    cv_types = {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan", "setting_out"}
    if dtype in cv_types:
        cv_data = process_floor_plan_image(img_path)
        extracted.update(cv_data)

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

            extracted = extract_page(page_arr, dtype, page_text, user_id)

            cv_types = {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan", "setting_out"}
            if dtype in cv_types:
                cv_data = process_floor_plan_image(img_path)
                extracted.update(cv_data)

            key = f"{page_info['pdf']}_p{page_info['page_num']}_{dtype}"
            results[key] = {**extracted, **page_info}

        except Exception as e:
            _log.exception("Worker extraction failed for page %s", page_info.get("page_num"))
            key = f"{page_info['pdf']}_p{page_info['page_num']}_{dtype}"
            results[key] = {"_ok": False, "_error": str(e), "drawing_type": dtype, **page_info}

    return {"extraction_results": results}


# ── Dispatcher ────────────────────────────────────────────────────

_PROCESSORS = {
    "pdf_extraction": _process_pdf_extraction,
    "ai_extraction": _process_ai_extraction,
    "full_pipeline": _process_full_pipeline,
}


def process_job(job: dict) -> dict:
    job_type = job["job_type"]
    processor = _PROCESSORS.get(job_type)
    if not processor:
        raise ValueError(f"No processor registered for job_type='{job_type}'")

    payload = job.get("payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    payload = payload or {}

    _log.info("Processing job #%s type=%s", job["id"], job_type)
    result = processor(payload)
    _log.info("Completed job #%s type=%s", job["id"], job_type)
    return result


def run_forever(poll_seconds: int = 5) -> None:
    _log.info("Worker started — polling every %ds", poll_seconds)
    while True:
        job = next_job()
        if not job:
            time.sleep(poll_seconds)
            continue
        job_id = int(job["id"])
        mark_job_started(job_id)
        try:
            result = process_job(job)
            mark_job_done(job_id, result)
        except Exception:
            _log.exception("Job #%d failed", job_id)
            mark_job_failed(job_id, traceback.format_exc())


if __name__ == "__main__":
    run_forever()
