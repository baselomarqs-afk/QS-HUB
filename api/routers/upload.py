from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, List
import os
import json

from api.auth import get_current_user
from utils.db import safe_query, safe_execute
from utils.storage import save_file
from pdf_engine.pdf_loader import load_pdf_pages, extract_page_text, page_to_pil

router = APIRouter()

CACHE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_qto_cache")
os.makedirs(CACHE_ROOT, exist_ok=True)

# Absolute safety ceiling (memory-DoS guard). The REAL per-file limit is the
# user's plan (max_file_mb) — this just caps truly absurd uploads. Keep it above
# the highest plan (admin = 500 MB) so it never overrides a legitimate plan.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "512")) * 1024 * 1024

@router.post("/upload")
async def upload_drawings(
    project_id: int = Form(...),
    str_files: List[UploadFile] = File([]),
    arch_files: List[UploadFile] = File([]),
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
    
    # Selective prefix cleanup to support sequential/chunked uploads
    if str_files:
        state_data["str_fnames"] = []
        state_data["str_texts"] = []
        state_data["str_boundaries"] = []
        state_data["str_page_count"] = 0
        for f in os.listdir(project_cache):
            if f.startswith("str_"):
                try: os.remove(os.path.join(project_cache, f))
                except: pass
    if arch_files:
        state_data["arch_fnames"] = []
        state_data["arch_texts"] = []
        state_data["arch_boundaries"] = []
        state_data["arch_page_count"] = 0
        for f in os.listdir(project_cache):
            if f.startswith("arch_"):
                try: os.remove(os.path.join(project_cache, f))
                except: pass

    # Helper function to process file and save page images
    def process_file(file_obj, prefix, start_idx):
        # Validate type & size before doing any work
        fname = (file_obj.filename or "").lower()
        ctype = (file_obj.content_type or "").lower()
        if not fname.endswith(".pdf") and "pdf" not in ctype:
            raise HTTPException(status_code=400, detail=f"Only PDF drawings are accepted (got '{file_obj.filename}').")
        # Cap the read at the user's PLAN file limit (bounded by an absolute
        # ceiling) so an oversized upload can't exhaust memory — and so a
        # higher-tier plan (Studio 200 MB / admin 500 MB) is never wrongly
        # blocked by a fixed number. Reading one byte past the cap is enough.
        from utils.plans import get_plan_for_user
        plan = get_plan_for_user(current_user["id"], current_user.get("role"))
        cap = min(plan.max_file_mb * 1024 * 1024, MAX_UPLOAD_BYTES)
        content = file_obj.file.read(cap + 1)
        if len(content) > cap:
            raise HTTPException(status_code=413, detail=f"File too large. Your plan allows up to {plan.max_file_mb} MB per file.")
        
        # Save to permanent storage (best-effort)
        try:
            save_file(current_user["id"], file_obj.filename, content, "application/pdf", project_id)
        except Exception as ex:
            print(f"save_file warning: {ex}")
        
        # Load texts for classification
        texts = extract_page_text(content)
        
        # 1. Fast Native Image Extraction to Disk (Bypasses slow Numpy/PIL pipeline entirely)
        from pdf_engine.pdf_loader import fast_save_pdf_pages
        page_count = fast_save_pdf_pages(content, project_id, prefix, start_idx)
        
        # Save the original PDF locally in cache for vector measurement
        pdf_cache_path = os.path.join(project_cache, f"{prefix}_{start_idx}.pdf")
        with open(pdf_cache_path, "wb") as f:
            f.write(content)
            
        return page_count, texts

    str_count = 0
    str_texts = []
    str_fnames = []
    str_boundaries = []
    for sf in str_files:
        if not sf.filename: continue
        start = str_count
        c, t = process_file(sf, "str", str_count)
        str_count += c
        str_texts.extend([txt[:2000] for txt in t])
        str_fnames.append(sf.filename)
        str_boundaries.append({"start": start, "end": str_count - 1, "pdf_path": f"str_{start}.pdf"})
        
    arch_count = 0
    arch_texts = []
    arch_fnames = []
    arch_boundaries = []
    for af in arch_files:
        if not af.filename: continue
        start = arch_count
        c, t = process_file(af, "arch", arch_count)
        arch_count += c
        arch_texts.extend([txt[:2000] for txt in t])
        arch_fnames.append(af.filename)
        arch_boundaries.append({"start": start, "end": arch_count - 1, "pdf_path": f"arch_{start}.pdf"})
        
    if str_files:
        state_data["str_fnames"] = str_fnames
        state_data["str_page_count"] = str_count
        state_data["str_texts"] = str_texts
        state_data["str_boundaries"] = str_boundaries
    if arch_files:
        state_data["arch_fnames"] = arch_fnames
        state_data["arch_page_count"] = arch_count
        state_data["arch_texts"] = arch_texts
        state_data["arch_boundaries"] = arch_boundaries

    # Save initial state back to database
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    df_exists = safe_query("SELECT id FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], project_id))
    if df_exists.empty:
        safe_execute(
            "INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data) VALUES (%s, %s, 1, %s)",
            (current_user["id"], project_id, state_json)
        )
    else:
        safe_execute(
            "UPDATE qto_active_projects SET current_step=1, state_data=%s WHERE user_id=%s AND project_id=%s",
            (state_json, current_user["id"], project_id)
        )
    
    return {
        "project_id": project_id,
        "str_fnames": state_data.get("str_fnames", []),
        "str_page_count": state_data.get("str_page_count", 0),
        "arch_fnames": state_data.get("arch_fnames", []),
        "arch_page_count": state_data.get("arch_page_count", 0),
        "next_step": 2
    }
