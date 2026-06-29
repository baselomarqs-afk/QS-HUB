"""Work Programme & Cash Flow module endpoints — saved history + per-project
credit consumption. The tools themselves run fully client-side; this only
persists results and enforces the 50-AED-per-project entitlement."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any

from api.auth import get_current_user
from utils.features import (
    FEATURES, get_credits, count_projects, consume_credit,
    save_module_project, list_module_projects, get_module_project, delete_module_project,
)

router = APIRouter()


class SaveModuleReq(BaseModel):
    project_id: Optional[int] = None
    name: str
    config: Dict[str, Any] = {}
    summary: Dict[str, Any] = {}


def _check_feature(feature: str):
    if feature not in FEATURES:
        raise HTTPException(status_code=404, detail="Unknown feature.")


@router.get("/{feature}")
async def list_history(feature: str, current_user: dict = Depends(get_current_user)):
    _check_feature(feature)
    return list_module_projects(current_user["id"], feature)


@router.get("/{feature}/item/{project_id}")
async def get_one(feature: str, project_id: int, current_user: dict = Depends(get_current_user)):
    _check_feature(feature)
    proj = get_module_project(current_user["id"], feature, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found.")
    return proj


@router.post("/{feature}/save")
async def save(feature: str, req: SaveModuleReq, current_user: dict = Depends(get_current_user)):
    _check_feature(feature)
    is_admin = current_user.get("role") == "admin"
    is_new = not req.project_id
    user_id = current_user["id"]
    
    if is_new and not is_admin:
        from utils.usage import check_limit, EVENT_PROJECT
        ok, msg = check_limit(current_user, EVENT_PROJECT)
        if not ok:
            raise HTTPException(status_code=403, detail=msg)
                
    pid = save_module_project(user_id, feature, req.name, req.config, req.summary, req.project_id)
    if pid is None:
        raise HTTPException(status_code=500, detail="Failed to save.")
        
    if is_new and not is_admin:
        from utils.usage import log_usage, EVENT_PROJECT
        log_usage(user_id, EVENT_PROJECT, metadata={"feature": feature, "project_id": pid, "project_name": req.name})
            
    return {"message": "Saved.", "project_id": pid}


@router.delete("/{feature}/item/{project_id}")
async def delete_one(feature: str, project_id: int, current_user: dict = Depends(get_current_user)):
    _check_feature(feature)
    ok, err = delete_module_project(current_user["id"], feature, project_id)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Delete failed: {err}")
    return {"message": "Deleted."}


import json
import re
from fastapi import UploadFile, File

@router.post("/spec/prefill")
async def spec_prefill(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    filename = file.filename or ""
    try:
        content = await file.read()
        if filename.lower().endswith(".pdf"):
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
        else:
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
        
    text = text.strip()
    if not text:
        return {"_success": False, "_error": "The specification file has no readable text."}
        
    from utils.key_manager import get_key_manager
    manager = get_key_manager()
    api_key, current_model = manager.get_key_and_model()
    if not api_key or api_key == "NO_API_KEY_FOUND":
        return {"_success": False, "_error": "No Gemini API key found. Please check Settings."}
        
    valid_types = ["G+0", "G+1", "G+2", "G+3", "G+4", "G+M", "G+M+1", "G+M+2", "B+G", "B+G+1", "B+G+2", "B+G+3"]
    valid_emirates = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "RAK", "UAQ", "Fujairah", "Other"]
    
    prompt = f"""You are a UAE quantity-surveying assistant. Read the villa project SPECIFICATION text and extract only the values you can determine WITH CONFIDENCE. This is for a private villa — there is no fire-fighting or fire-alarm scope.

Return STRICT JSON: {{ "suggestions": {{ ... }}, "confidence": "high|medium|low", "notes": "short note" }}.
Inside "suggestions", include ONLY keys you found; OMIT anything not stated in the text (do not guess). Use these keys and types:
- villaType: one of {", ".join(valid_types)} (floor configuration).
- buaPerFloor: number (m² built-up area of a typical floor).
- basementArea, mezzanineArea: number (m², only if present).
- projectName, clientName, plotNumber, consultantName, contractorName: string.
- location: one of {", ".join(valid_emirates)}.
- hasPool, hasRoofGarden, hasExternalLandscape, hasBoundaryWall, hasDemolition: boolean.
- complexityFactor: 0.8 (simple), 1.0 (standard) or 1.2 (complex/high-end finishes).
- contractValueAed: number (AED).
- advancePaymentPct, retentionPct, vatPct: number (percent).
- certificationPeriodDays, paymentPeriodDays: number (days).
- defectsLiabilityMonths: number (months).

SPECIFICATION:
{text[:24000]}"""

    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=current_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        
        raw = response.text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(raw)
        
        suggestions = parsed.get("suggestions", {})
        sanitized = {}
        
        def to_num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
                
        def to_bool(v):
            if isinstance(v, bool):
                return v
            if str(v).lower() in ("true", "1", "yes"):
                return True
            if str(v).lower() in ("false", "0", "no"):
                return False
            return None

        # Strings
        for k in ("projectName", "clientName", "plotNumber", "consultantName", "contractorName"):
            if k in suggestions and suggestions[k]:
                sanitized[k] = str(suggestions[k]).strip()
                
        # Numbers
        for k in ("buaPerFloor", "basementArea", "mezzanineArea", "contractValueAed", 
                  "advancePaymentPct", "retentionPct", "vatPct", "certificationPeriodDays", 
                  "paymentPeriodDays", "defectsLiabilityMonths"):
            if k in suggestions:
                val = to_num(suggestions[k])
                if val is not None and val >= 0:
                    sanitized[k] = val
                    
        # Booleans
        for k in ("hasPool", "hasRoofGarden", "hasExternalLandscape", "hasBoundaryWall", "hasDemolition"):
            if k in suggestions:
                val = to_bool(suggestions[k])
                if val is not None:
                    sanitized[k] = val
                    
        # Specials
        if "villaType" in suggestions:
            vt = str(suggestions["villaType"]).upper().strip()
            if vt in valid_types:
                sanitized["villaType"] = vt
        if "location" in suggestions:
            loc = str(suggestions["location"]).strip()
            matching = [e for e in valid_emirates if e.lower() == loc.lower()]
            if matching:
                sanitized["location"] = matching[0]
                
        if "complexityFactor" in suggestions:
            cf = to_num(suggestions["complexityFactor"])
            if cf is not None:
                sanitized["complexityFactor"] = 0.8 if cf < 0.9 else (1.2 if cf > 1.1 else 1.0)
                
        return {
            "_success": True,
            "suggestions": sanitized,
            "confidence": parsed.get("confidence", "low"),
            "notes": parsed.get("notes", "")
        }
    except Exception as e:
        return {"_success": False, "_error": f"AI extraction failed: {str(e)}"}

