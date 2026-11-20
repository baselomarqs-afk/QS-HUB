"""Work Programme & Cash Flow module endpoints — saved history + per-project
credit consumption + robust AI specification pre-fill (text & scanned PDFs)."""
import json
import re
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from api.auth import get_current_user
from utils.features import (
    FEATURES,
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
        ok, msg = check_limit(current_user, EVENT_PROJECT, feature=feature)
        if not ok:
            raise HTTPException(status_code=403, detail=msg)

    pid = save_module_project(user_id, feature, req.name, req.config, req.summary, req.project_id)
    if pid is None:
        raise HTTPException(status_code=500, detail="Failed to save.")

    if is_new and not is_admin:
        from utils.usage import settle_project_creation
        settle_project_creation(current_user, feature, {"project_id": pid, "project_name": req.name})

    return {"message": "Saved.", "project_id": pid}


@router.delete("/{feature}/item/{project_id}")
async def delete_one(feature: str, project_id: int, current_user: dict = Depends(get_current_user)):
    _check_feature(feature)
    ok, err = delete_module_project(current_user["id"], feature, project_id)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Delete failed: {err}")
    return {"message": "Deleted."}


def _sanitize_prefill(parsed: dict) -> dict:
    valid_types = ["G+0", "G+1", "G+2", "G+3", "G+4", "G+M", "G+M+1", "G+M+2", "B+G", "B+G+1", "B+G+2", "B+G+3"]
    valid_emirates = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "RAK", "UAQ", "Fujairah", "Other"]
    suggestions = parsed.get("suggestions", {}) or {}
    sanitized: Dict[str, Any] = {}

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

    for k in ("projectName", "clientName", "plotNumber", "consultantName", "contractorName"):
        if k in suggestions and suggestions[k]:
            sanitized[k] = str(suggestions[k]).strip()

    for k in (
        "buaPerFloor", "basementArea", "mezzanineArea", "contractValueAed",
        "advancePaymentPct", "retentionPct", "vatPct", "certificationPeriodDays",
        "paymentPeriodDays", "defectsLiabilityMonths",
    ):
        if k in suggestions:
            val = to_num(suggestions[k])
            if val is not None and val >= 0:
                sanitized[k] = val

    for k in ("hasPool", "hasRoofGarden", "hasExternalLandscape", "hasBoundaryWall", "hasDemolition"):
        if k in suggestions:
            val = to_bool(suggestions[k])
            if val is not None:
                sanitized[k] = val

    if "villaType" in suggestions:
        vt = str(suggestions["villaType"]).upper().strip()
        if vt in valid_types:
            sanitized["villaType"] = vt

    if "foundationType" in suggestions:
        ft = str(suggestions["foundationType"]).lower().strip()
        if "raft" in ft or "mat" in ft:
            sanitized["foundationType"] = "raft"
        elif "isolat" in ft or "pad" in ft or "footing" in ft:
            sanitized["foundationType"] = "isolated"

    if "location" in suggestions:
        loc = str(suggestions["location"]).strip()
        matching = [e for e in valid_emirates if e.lower() == loc.lower()]
        if matching:
            sanitized["location"] = matching[0]

    if "complexityFactor" in suggestions:
        cf = to_num(suggestions["complexityFactor"])
        if cf is not None:
            sanitized["complexityFactor"] = 0.8 if cf < 0.9 else (1.2 if cf > 1.1 else 1.0)

    return sanitized


@router.post("/spec/prefill")
async def spec_prefill(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    filename = file.filename or ""
    text = ""
    scanned_images = []
    try:
        content = await file.read()
        if filename.lower().endswith(".pdf"):
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                text += page.get_text()
            # Scanned PDF fallback: render up to first 6 pages for Gemini Vision
            if len(text.strip()) < 80 and len(doc) > 0:
                max_pages = min(len(doc), 6)
                for idx in range(max_pages):
                    pix = doc[idx].get_pixmap(dpi=150)
                    scanned_images.append(pix.tobytes("png"))
            doc.close()
        else:
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    text = text.strip()
    if not text and not scanned_images:
        return {"_success": False, "_error": "The specification file has no readable text or pages."}

    from utils.key_manager import get_key_manager
    manager = get_key_manager()

    valid_types = ["G+0", "G+1", "G+2", "G+3", "G+4", "G+M", "G+M+1", "G+M+2", "B+G", "B+G+1", "B+G+2", "B+G+3"]
    valid_emirates = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "RAK", "UAQ", "Fujairah", "Other"]

    base_instructions = f"""You are a UAE quantity-surveying assistant. Read the villa project SPECIFICATION and extract only the values you can determine WITH CONFIDENCE. This is for a private villa — there is no fire-fighting or fire-alarm scope.

Return STRICT JSON: {{ "suggestions": {{ ... }}, "confidence": "high|medium|low", "notes": "short note" }}.
Inside "suggestions", include ONLY keys you found; OMIT anything not stated (do not guess). Use these keys and types:
- villaType: one of {", ".join(valid_types)} (floor configuration).
- foundationType: "isolated" (isolated footings / tie beams) or "raft" (raft / mat foundation), only if stated.
- buaPerFloor: number (m² built-up area of a typical floor).
- basementArea, mezzanineArea: number (m², only if present).
- projectName, clientName, plotNumber, consultantName, contractorName: string.
- location: one of {", ".join(valid_emirates)}.
- hasPool, hasRoofGarden, hasExternalLandscape, hasBoundaryWall, hasDemolition: boolean.
- complexityFactor: 0.8 (simple), 1.0 (standard) or 1.2 (complex/high-end finishes).
- contractValueAed: number (AED).
- advancePaymentPct, retentionPct, vatPct: number (percent).
- certificationPeriodDays, paymentPeriodDays: number (days).
- defectsLiabilityMonths: number (months)."""

    from google import genai
    from google.genai import types

    if scanned_images:
        contents: Any = [base_instructions + "\n\nRead the attached scanned specification pages:"]
        for img_bytes in scanned_images:
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    else:
        contents = f"{base_instructions}\n\nSPECIFICATION:\n{text[:24000]}"

    # Rotate across all configured Gemini API keys & fallback models on transient / quota errors
    import asyncio
    num_keys = len(getattr(manager, "_keys", []))
    max_attempts = max(6, min(num_keys * 2, 24))
    last_err = ""
    for _ in range(max_attempts):
        api_key, current_model = manager.get_key_and_model()
        if not api_key or api_key == "NO_API_KEY_FOUND":
            return {"_success": False, "_error": "No Gemini API key found. Please check Settings."}
        try:
            def _call_gemini(key=api_key, mdl=current_model):
                client = genai.Client(api_key=key, http_options={"timeout": 45.0})
                return client.models.generate_content(
                    model=mdl,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0,
                    ),
                )

            response = await asyncio.to_thread(_call_gemini)
            raw = (response.text or "").strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(raw)
            sanitized = _sanitize_prefill(parsed)
            return {
                "_success": True,
                "suggestions": sanitized,
                "confidence": parsed.get("confidence", "low"),
                "notes": parsed.get("notes", ""),
            }
        except Exception as e:
            last_err = str(e)
            err_low = last_err.lower()
            if "404" in err_low or "not found" in err_low:
                manager.mark_model_unavailable(current_model)
                continue
            is_retryable = any(tok in err_low for tok in ("429", "quota", "resource_exhausted", "503", "unavailable", "timeout", "deadline", "overloaded"))
            if is_retryable:
                manager.mark_rate_limited(api_key, current_model)
                continue
            break

    return {"_success": False, "_error": f"AI extraction failed: {last_err}"}
