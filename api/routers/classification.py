from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import json
import numpy as np
from PIL import Image

from api.auth import get_current_user
from utils.db import safe_query, safe_execute
from pdf_engine.smart_classifier import PAGE_ITEMS_MAP
from workflow.step2_classify import _classify_single, _ai_classify

router = APIRouter()

CACHE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_qto_cache")
os.makedirs(CACHE_ROOT, exist_ok=True)

class RunExtractionReq(BaseModel):
    project_id: int

class SaveClassificationReq(BaseModel):
    project_id: int
    classified_pages: List[Dict[str, Any]]

@router.post("/classify/auto")
async def auto_classify(req: RunExtractionReq, current_user: dict = Depends(get_current_user)):
    df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], req.project_id))
    if df_state.empty or not df_state.iloc[0]["state_data"]:
        raise HTTPException(status_code=400, detail="No active project uploaded.")
        
    state_data = json.loads(df_state.iloc[0]["state_data"])
    project_cache = os.path.join(CACHE_ROOT, str(req.project_id))
    
    str_texts = state_data.get("str_texts") or []
    arch_texts = state_data.get("arch_texts") or []

    # Safety fallback: re-extract text directly from PDF ONLY if stored text is missing
    from pdf_engine.pdf_loader import extract_page_text
    str_boundaries = state_data.get("str_boundaries") or []
    if str_boundaries and not str_texts:
        reextracted = []
        for b in str_boundaries:
            pdf_p = os.path.join(project_cache, b.get("pdf_path", ""))
            if os.path.exists(pdf_p):
                with open(pdf_p, "rb") as f:
                    reextracted.extend(extract_page_text(f.read()))
        if reextracted:
            str_texts = reextracted

    arch_boundaries = state_data.get("arch_boundaries") or []
    if arch_boundaries and not arch_texts:
        reextracted = []
        for b in arch_boundaries:
            pdf_p = os.path.join(project_cache, b.get("pdf_path", ""))
            if os.path.exists(pdf_p):
                with open(pdf_p, "rb") as f:
                    reextracted.extend(extract_page_text(f.read()))
        if reextracted:
            arch_texts = reextracted
    
    classified = []
    
    # Keyword classification
    for i, txt in enumerate(str_texts):
        ext = "jpg" if os.path.exists(os.path.join(project_cache, f"str_page_{i}.jpg")) else "png"
        classified.append({
            "pdf": "structural",
            "page_index": i,
            "page_num": i + 1,
            "text_preview": txt[:100].replace("\n", " "),
            "image_url": f"/cache/{req.project_id}/str_page_{i}.{ext}",
            **_classify_single(txt, "structural"),
        })
        
    for i, txt in enumerate(arch_texts):
        ext = "jpg" if os.path.exists(os.path.join(project_cache, f"arch_page_{i}.jpg")) else "png"
        classified.append({
            "pdf": "architectural",
            "page_index": i,
            "page_num": i + 1,
            "text_preview": txt[:100].replace("\n", " "),
            "image_url": f"/cache/{req.project_id}/arch_page_{i}.{ext}",
            **_classify_single(txt, "architectural"),
        })

    # AI Vision classification for low confidence pages (in a real production app we run this, but limit calls)
    project_cache = os.path.join(CACHE_ROOT, str(req.project_id))
    from concurrent.futures import ThreadPoolExecutor

    def process_page(p):
        # Fast path: Keyword classification in _classify_single is instant (0.01s).
        # Bypass slow remote AI vision calls during auto-classify to prevent proxy timeouts and 502 Bad Gateway errors.
        return p

    state_data["classified_pages"] = classified
    state_data["current_step"] = 2
    
    from utils.db import upsert_active_state
    upsert_active_state(current_user["id"], req.project_id, 2, state_data)
    
    return {
        "classified_pages": classified,
        "next_step": 3
    }

def _background_record_memory(user_id: int, pages: list):
    try:
        from engine.qto_memory import record_mapping
        for p in pages:
            dtype = (p.get("detected_type") or "").strip()
            if dtype and dtype != "unknown":
                record_mapping(user_id, dtype[:120], dtype)
    except Exception as e:
        print(f"qto_memory record error: {e}")

@router.post("/classify/save")
async def save_classification(req: SaveClassificationReq, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    try:
        df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], req.project_id))
        
        state_data = {}
        if not df_state.empty and df_state.iloc[0]["state_data"]:
            try:
                state_data = json.loads(df_state.iloc[0]["state_data"])
            except Exception:
                state_data = {}
        
        state_data["classified_pages"] = req.classified_pages
        state_data["current_step"] = 3
        
        from utils.db import upsert_active_state
        success, msg = upsert_active_state(current_user["id"], req.project_id, 3, state_data)

        if not success:
            print(f"[classify/save] DB ERROR: {msg}")
            raise HTTPException(status_code=500, detail=f"DB error: {msg}")

        # Learning loop pushed to background to prevent 502 Proxy Timeout
        background_tasks.add_task(_background_record_memory, current_user["id"], req.classified_pages or [])

        return {"message": "Classifications saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[classify/save] UNHANDLED ERROR: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
