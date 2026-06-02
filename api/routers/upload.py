from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
import os
import json

from api.auth import get_current_user
from utils.db import safe_query, safe_execute
from utils.storage import save_file
from pdf_engine.pdf_loader import load_pdf_pages, extract_page_text, page_to_pil

router = APIRouter()

CACHE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_qto_cache")
os.makedirs(CACHE_ROOT, exist_ok=True)

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "50")) * 1024 * 1024

@router.post("/upload")
async def upload_drawings(
    project_id: int = Form(...),
    str_file: Optional[UploadFile] = File(None),
    arch_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    # Verify project belongs to user
    df = safe_query("SELECT id FROM qto_projects WHERE id=%s AND user_id=%s", (project_id, current_user["id"]))
    if df.empty:
        raise HTTPException(status_code=404, detail="Project not found or access denied.")

    project_cache = os.path.join(CACHE_ROOT, str(project_id))
    os.makedirs(project_cache, exist_ok=True)
    
    state_data = {}
    
    # Load existing state if any
    df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], project_id))
    if not df_state.empty and df_state.iloc[0]["state_data"]:
        try:
            state_data = json.loads(df_state.iloc[0]["state_data"])
        except:
            pass

    # Clear old pipeline data
    state_data["classified_pages"] = []
    state_data["extraction_results"] = {}
    state_data["confirmed_auto_data"] = {}
    state_data["current_step"] = 1
    
    # Cleanup previous cached images
    for f in os.listdir(project_cache):
        try: os.remove(os.path.join(project_cache, f))
        except: pass

    # Helper function to process file and save page images
    def process_file(file_obj, prefix):
        # Validate type & size before doing any work
        fname = (file_obj.filename or "").lower()
        ctype = (file_obj.content_type or "").lower()
        if not fname.endswith(".pdf") and "pdf" not in ctype:
            raise HTTPException(status_code=400, detail=f"Only PDF drawings are accepted (got '{file_obj.filename}').")
        content = file_obj.file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")
        
        # Save to permanent storage
        save_file(current_user["id"], file_obj.filename, content, "application/pdf", project_id)
        
        # Load pages and text
        pages = load_pdf_pages(content)
        texts = extract_page_text(content)
        
        # Convert pages (numpy arrays) to PNG and save to cache
        for idx, page_arr in enumerate(pages):
            pil_img = page_to_pil(page_arr)
            # Resize if too large to save space and load fast
            w, h = pil_img.size
            if max(w, h) > 1600:
                scale = 1600 / max(w, h)
                pil_img = pil_img.resize((int(w * scale), int(h * scale)))
            pil_img.save(os.path.join(project_cache, f"{prefix}_page_{idx}.png"), format="PNG")
            
        return len(pages), texts

    str_count, arch_count = 0, 0
    if str_file:
        str_count, str_texts = process_file(str_file, "str")
        state_data["str_fname"] = str_file.filename
        state_data["str_page_count"] = str_count
        state_data["str_texts"] = str_texts
        
    if arch_file:
        arch_count, arch_texts = process_file(arch_file, "arch")
        state_data["arch_fname"] = arch_file.filename
        state_data["arch_page_count"] = arch_count
        state_data["arch_texts"] = arch_texts

    # Save initial state back to database
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    from utils.db import is_sqlite
    if is_sqlite():
        safe_execute(
            """
            INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(user_id, project_id) DO UPDATE SET 
                current_step=excluded.current_step, 
                state_data=excluded.state_data, 
                updated_at=datetime('now', 'localtime')
            """,
            (current_user["id"], project_id, 1, state_json)
        )
    else:
        safe_execute(
            """
            INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE current_step=%s, state_data=%s, updated_at=CURRENT_TIMESTAMP
            """,
            (current_user["id"], project_id, 1, state_json, 1, state_json)
        )
    
    return {
        "project_id": project_id,
        "str_fname": state_data.get("str_fname"),
        "str_page_count": str_count,
        "arch_fname": state_data.get("arch_fname"),
        "arch_page_count": arch_count,
        "next_step": 2
    }
