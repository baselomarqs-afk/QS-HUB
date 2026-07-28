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
    
    # Re-extract FULL text from cached PDFs on disk for accurate keyword classification.
    # The DB only stores truncated 250-char previews to stay under packet limits,
    # but keyword matching needs the full page text. Reading from disk via mmap is
    # instant and uses virtually no RAM.
    from pdf_engine.pdf_loader import extract_page_text
    
    str_boundaries = state_data.get("str_boundaries") or []
    str_texts = []
    for b in str_boundaries:
        pdf_p = os.path.join(project_cache, b.get("pdf_path", ""))
        exists = os.path.exists(pdf_p)
        print(f"[classify/auto] STR PDF path={pdf_p} exists={exists}")
        if exists:
            extracted = extract_page_text(pdf_p)
            print(f"[classify/auto] STR extracted {len(extracted)} pages, first 200 chars: {extracted[0][:200] if extracted else '(none)'}")
            str_texts.extend(extracted)
    
    # Fallback to DB-stored (truncated) texts if PDFs are missing from disk
    if not str_texts:
        str_texts = state_data.get("str_texts") or []
    
    arch_boundaries = state_data.get("arch_boundaries") or []
    arch_texts = []
    for b in arch_boundaries:
        pdf_p = os.path.join(project_cache, b.get("pdf_path", ""))
        exists = os.path.exists(pdf_p)
        print(f"[classify/auto] ARCH PDF path={pdf_p} exists={exists}")
        if exists:
            extracted = extract_page_text(pdf_p)
            print(f"[classify/auto] ARCH extracted {len(extracted)} pages, first 200 chars: {extracted[0][:200] if extracted else '(none)'}")
            arch_texts.extend(extracted)
    
    if not arch_texts:
        arch_texts = state_data.get("arch_texts") or []
    
    classified = []
    
    # Keyword classification using full page text
    for i, txt in enumerate(str_texts):
        classified.append({
            "pdf": "structural",
            "page_index": i,
            "page_num": i + 1,
            "text_preview": txt[:100].replace("\n", " "),
            "image_url": f"/cache/{req.project_id}/str_page_{i}.jpg",
            **_classify_single(txt, "structural"),
        })
        
    for i, txt in enumerate(arch_texts):
        classified.append({
            "pdf": "architectural",
            "page_index": i,
            "page_num": i + 1,
            "text_preview": txt[:100].replace("\n", " "),
            "image_url": f"/cache/{req.project_id}/arch_page_{i}.jpg",
            **_classify_single(txt, "architectural"),
        })

    state_data["classified_pages"] = classified
    state_data["current_step"] = 2
    
    from utils.db import upsert_active_state
    upsert_active_state(current_user["id"], req.project_id, 2, state_data)
    
    return {
        "classified_pages": classified,
        "next_step": 3,
        "_debug": {
            "cache_dir": project_cache,
            "cache_exists": os.path.isdir(project_cache),
            "cache_files": os.listdir(project_cache) if os.path.isdir(project_cache) else [],
            "str_boundaries": str_boundaries,
            "arch_boundaries": arch_boundaries,
            "str_texts_count": len(str_texts),
            "arch_texts_count": len(arch_texts),
            "str_text_sample": str_texts[0][:300] if str_texts else "(empty)",
            "arch_text_sample": arch_texts[0][:300] if arch_texts else "(empty)",
            "unknown_count": sum(1 for p in classified if p.get("detected_type") == "unknown"),
            "total_classified": len(classified),
        }
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
