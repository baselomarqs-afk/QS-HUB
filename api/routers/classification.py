from fastapi import APIRouter, HTTPException, Depends
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
    
    str_texts = state_data.get("str_texts") or []
    arch_texts = state_data.get("arch_texts") or []
    
    classified = []
    
    # Keyword classification
    for i, txt in enumerate(str_texts):
        classified.append({
            "pdf": "structural",
            "page_index": i,
            "page_num": i + 1,
            "text_preview": txt[:100].replace("\n", " "),
            "image_url": f"/cache/{req.project_id}/str_page_{i}.png",
            **_classify_single(txt, "structural"),
        })
        
    for i, txt in enumerate(arch_texts):
        classified.append({
            "pdf": "architectural",
            "page_index": i,
            "page_num": i + 1,
            "text_preview": txt[:100].replace("\n", " "),
            "image_url": f"/cache/{req.project_id}/arch_page_{i}.png",
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
    
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    safe_execute(
        "UPDATE qto_active_projects SET current_step=2, state_data=%s WHERE user_id=%s AND project_id=%s",
        (state_json, current_user["id"], req.project_id)
    )
    
    return {
        "classified_pages": classified,
        "next_step": 3
    }

@router.post("/classify/save")
async def save_classification(req: SaveClassificationReq, current_user: dict = Depends(get_current_user)):
    df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], req.project_id))
    
    state_data = {}
    if not df_state.empty and df_state.iloc[0]["state_data"]:
        try:
            state_data = json.loads(df_state.iloc[0]["state_data"])
        except Exception:
            state_data = {}
            
    state_data["classified_pages"] = req.classified_pages
    state_data["current_step"] = 3
    
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    
    from utils.db import is_sqlite
    if is_sqlite():
        success, msg = safe_execute(
            """
            INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(user_id, project_id) DO UPDATE SET 
                current_step=excluded.current_step, 
                state_data=excluded.state_data, 
                updated_at=datetime('now', 'localtime')
            """,
            (current_user["id"], req.project_id, 3, state_json)
        )
    else:
        success, msg = safe_execute(
            """
            INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE current_step=VALUES(current_step), state_data=VALUES(state_data)
            """,
            (current_user["id"], req.project_id, 3, state_json)
        )

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update database: {msg}")

    # Learning loop (API path): capture the user-confirmed page classifications so
    # the AI improves over time. Approved rules are injected back into extraction
    # via engine.qto_memory.format_rules_for_prompt (already wired in step3_extract).
    try:
        from engine.qto_memory import record_mapping
        for p in (req.classified_pages or []):
            dtype = (p.get("detected_type") or "").strip()
            text = (p.get("text_preview") or "").strip()
            if dtype and dtype != "unknown" and len(text) > 8:
                record_mapping(current_user["id"], text[:120], dtype)
    except Exception as e:
        print(f"qto_memory record error: {e}")

    return {"message": "Classifications saved successfully."}
