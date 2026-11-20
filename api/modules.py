"""Work Programme & Cash Flow module endpoints — saved history, per-project
credit consumption, AI specification pre-fill, and AI villa drawing analyzer
(reads architectural/structural PDFs & images to extract real villa parameters)."""
import asyncio
import json
import re
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from api.auth import get_current_user
from utils.features import (
    FEATURES,
    save_module_project, list_module_projects, get_module_project, delete_module_project,
)

router = APIRouter()

VALID_VILLA_TYPES = ["G+0", "G+1", "G+2", "G+3", "G+4", "G+M", "G+M+1", "G+M+2", "B+G", "B+G+1", "B+G+2", "B+G+3"]
VALID_EMIRATES = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "RAK", "UAQ", "Fujairah", "Other"]


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
                sanitized[k] = round(val, 2)

    for k in ("hasPool", "hasRoofGarden", "hasExternalLandscape", "hasBoundaryWall", "hasDemolition"):
        if k in suggestions:
            val = to_bool(suggestions[k])
            if val is not None:
                sanitized[k] = val

    if "villaType" in suggestions:
        vt = str(suggestions["villaType"]).upper().strip().replace(" ", "")
        if vt in VALID_VILLA_TYPES:
            sanitized["villaType"] = vt

    if "foundationType" in suggestions:
        ft = str(suggestions["foundationType"]).lower().strip()
        if "raft" in ft or "mat" in ft:
            sanitized["foundationType"] = "raft"
        elif "isolat" in ft or "pad" in ft or "footing" in ft or "tie" in ft:
            sanitized["foundationType"] = "isolated"

    if "location" in suggestions:
        loc = str(suggestions["location"]).strip()
        matching = [e for e in VALID_EMIRATES if e.lower() == loc.lower()]
        if matching:
            sanitized["location"] = matching[0]

    if "complexityFactor" in suggestions:
        cf = to_num(suggestions["complexityFactor"])
        if cf is not None:
            sanitized["complexityFactor"] = 0.8 if cf < 0.9 else (1.2 if cf > 1.1 else 1.0)

    return sanitized


async def _run_gemini_json(contents: Any, timeout_s: float = 55.0) -> Tuple[Optional[dict], Optional[str]]:
    """Run Gemini JSON generation with automatic 2D rotation across all keys & models."""
    from utils.key_manager import get_key_manager
    from google import genai
    from google.genai import types

    manager = get_key_manager()
    num_keys = len(getattr(manager, "_keys", []))
    max_attempts = max(6, min(num_keys * 2, 24))
    last_err = ""

    for _ in range(max_attempts):
        api_key, current_model = manager.get_key_and_model()
        if not api_key or api_key == "NO_API_KEY_FOUND":
            return None, "No Gemini API key found. Please check Settings."
        try:
            def _call_gemini(key=api_key, mdl=current_model):
                client = genai.Client(api_key=key, http_options={"timeout": timeout_s})
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
            return json.loads(raw), None
        except Exception as e:
            last_err = str(e)
            err_low = last_err.lower()
            if "404" in err_low or "not found" in err_low:
                manager.mark_model_unavailable(current_model)
                continue
            is_retryable = any(
                tok in err_low
                for tok in ("429", "quota", "resource_exhausted", "503", "unavailable", "timeout", "deadline", "overloaded")
            )
            if is_retryable:
                manager.mark_rate_limited(api_key, current_model)
                continue
            break

    return None, f"AI extraction failed: {last_err}"


def _score_drawing_page(page_idx: int, page_text: str) -> Tuple[int, str]:
    """Score a PDF drawing sheet for visual priority when summarizing a villa project."""
    up = (page_text or "").upper()
    score = 0
    tag = "general"

    if page_idx == 0:
        score += 4
    if any(k in up for k in ("AREA SCHEDULE", "AREA TABLE", "BUA", "BUILT UP", "BUILT-UP", "SUMMARY OF AREA", "GFA")):
        score += 12
        tag = "area_schedule"
    if any(k in up for k in ("FOUNDATION", "FOOTING", "RAFT", "TIE BEAM", "SUBSTRUCTURE", "SHORING")):
        score += 10
        tag = "foundation"
    if any(k in up for k in ("SITE PLAN", "PLOT PLAN", "SETTING OUT", "MASTER PLAN", "LANDSCAPE", "BOUNDARY WALL", "SWIMMING POOL")):
        score += 9
        tag = "site_plan"
    if any(k in up for k in ("GROUND FLOOR", "G.F. PLAN", "GF PLAN")):
        score += 9
        tag = "ground_floor"
    if any(k in up for k in ("FIRST FLOOR", "1ST FLOOR", "SECOND FLOOR", "2ND FLOOR", "THIRD FLOOR", "BASEMENT", "MEZZANINE")):
        score += 8
        tag = "upper_or_basement"
    if any(k in up for k in ("ROOF PLAN", "ROOF FLOOR", "UPPER ROOF", "ROOF GARDEN", "PARAPET")):
        score += 7
        tag = "roof_plan"
    if any(k in up for k in ("SECTION", "ELEVATION")):
        score += 5
        tag = "elevation_section"
    if any(k in up for k in ("DOOR SCHEDULE", "WINDOW SCHEDULE", "DETAIL", "STAIRCASE DETAIL", "MEP", "SINGLE LINE")):
        score -= 3

    return score, tag


def _extract_drawing_evidence(file_entries: List[Tuple[str, bytes, str]], max_visual_pages: int = 5) -> dict:
    """Scan all uploaded drawing PDFs & images, extracting compact text from every page
    and rendering up to `max_visual_pages` highest-value sheets as JPEGs for Vision AI."""
    import fitz

    text_snippets: List[str] = []
    candidates: List[Tuple[int, str, bytes, str]] = []  # (score, label, jpeg_bytes, mime)
    total_pages = 0
    files_summary: List[dict] = []

    for fname, raw_bytes, content_type in file_entries:
        low = fname.lower()
        is_pdf = low.endswith(".pdf") or content_type == "application/pdf"
        if is_pdf:
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
            page_count = len(doc)
            total_pages += page_count
            files_summary.append({"name": fname, "pages": page_count, "type": "pdf"})

            scored_pages = []
            for p_idx in range(page_count):
                ptxt = (doc[p_idx].get_text() or "").strip()
                compact = re.sub(r"\s+", " ", ptxt)[:900]
                if compact:
                    text_snippets.append(f"[{fname} — Page {p_idx + 1}/{page_count}]: {compact}")
                score, tag = _score_drawing_page(p_idx, ptxt)
                scored_pages.append((score, tag, p_idx))

            # Pick diverse top sheets from this PDF (at most 1 per tag first, then fill)
            scored_pages.sort(key=lambda x: (-x[0], x[2]))
            picked: List[Tuple[int, str, int]] = []
            seen_tags: Dict[str, int] = {}
            per_file_cap = min(max_visual_pages, max(2, max_visual_pages // max(1, len(file_entries)) + 1))
            for score, tag, p_idx in scored_pages:
                if len(picked) >= per_file_cap:
                    break
                if seen_tags.get(tag, 0) >= 1 and len(scored_pages) > per_file_cap:
                    continue
                seen_tags[tag] = seen_tags.get(tag, 0) + 1
                picked.append((score, tag, p_idx))
            # If PDF is scanned (zero text on all pages), guarantee evenly spread pages
            if not any(s > 4 for s, _, _ in scored_pages) and page_count > 1:
                step = max(1, page_count // min(page_count, per_file_cap))
                picked = [(4, "scanned", idx) for idx in range(0, page_count, step)][:per_file_cap]

            seen_p = set()
            for sc, tg, p_idx in sorted(picked, key=lambda x: x[2]):
                if p_idx in seen_p:
                    continue
                seen_p.add(p_idx)
                page = doc[p_idx]
                # Cap longest edge at 1280px JPEG q=78 — crisp title blocks & fast Vision latency
                rect = page.rect
                longest = max(rect.width, rect.height, 1.0)
                zoom = min(120.0 / 72.0, 1280.0 / longest)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                jpg_bytes = pix.tobytes("jpeg", jpg_quality=78)
                candidates.append((sc + (2 if p_idx == 0 else 0), f"{fname} (p.{p_idx + 1}, {tg})", jpg_bytes, "image/jpeg"))
            doc.close()
        elif content_type.startswith("image/") or low.endswith((".png", ".jpg", ".jpeg", ".webp")):
            total_pages += 1
            files_summary.append({"name": fname, "pages": 1, "type": "image"})
            mime = content_type if content_type.startswith("image/") else "image/png"
            candidates.append((10, fname, raw_bytes, mime))

    candidates.sort(key=lambda x: -x[0])
    selected_visuals = candidates[:max_visual_pages]

    return {
        "total_pages": total_pages,
        "visual_count": len(selected_visuals),
        "files_summary": files_summary,
        "text_summary": "\n".join(text_snippets)[:20000],
        "visuals": selected_visuals,
    }


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

    base_instructions = f"""You are a UAE quantity-surveying assistant. Read the villa project SPECIFICATION and extract only the values you can determine WITH CONFIDENCE. This is for a private villa — there is no fire-fighting or fire-alarm scope.

Return STRICT JSON: {{ "suggestions": {{ ... }}, "confidence": "high|medium|low", "notes": "short note" }}.
Inside "suggestions", include ONLY keys you found; OMIT anything not stated (do not guess). Use these keys and types:
- villaType: one of {", ".join(VALID_VILLA_TYPES)} (floor configuration).
- foundationType: "isolated" (isolated footings / tie beams) or "raft" (raft / mat foundation), only if stated.
- buaPerFloor: number (m² built-up area of a typical floor).
- basementArea, mezzanineArea: number (m², only if present).
- projectName, clientName, plotNumber, consultantName, contractorName: string.
- location: one of {", ".join(VALID_EMIRATES)}.
- hasPool, hasRoofGarden, hasExternalLandscape, hasBoundaryWall, hasDemolition: boolean.
- complexityFactor: 0.8 (simple), 1.0 (standard) or 1.2 (complex/high-end finishes).
- contractValueAed: number (AED).
- advancePaymentPct, retentionPct, vatPct: number (percent).
- certificationPeriodDays, paymentPeriodDays: number (days).
- defectsLiabilityMonths: number (months)."""

    from google.genai import types

    if scanned_images:
        contents: Any = [base_instructions + "\n\nRead the attached scanned specification pages:"]
        for img_bytes in scanned_images:
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    else:
        contents = f"{base_instructions}\n\nSPECIFICATION:\n{text[:24000]}"

    parsed, err = await _run_gemini_json(contents, timeout_s=45.0)
    if err or not parsed:
        return {"_success": False, "_error": err or "AI extraction failed."}

    sanitized = _sanitize_prefill(parsed)
    return {
        "_success": True,
        "suggestions": sanitized,
        "confidence": parsed.get("confidence", "low"),
        "notes": parsed.get("notes", ""),
    }


@router.post("/drawings/analyze")
async def analyze_drawings(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Actively read uploaded villa architectural/structural drawings (PDFs or images)
    using PyMuPDF text sweep + Gemini Vision to extract real villa schedule parameters."""
    if not files:
        raise HTTPException(status_code=400, detail="No drawing files uploaded.")

    file_entries: List[Tuple[str, bytes, str]] = []
    for f in files[:8]:  # Cap at 8 drawing files per analysis call
        raw = await f.read()
        if raw:
            file_entries.append((f.filename or "drawing.pdf", raw, f.content_type or ""))

    if not file_entries:
        return {"_success": False, "_error": "Uploaded drawing files are empty."}

    try:
        evidence = await asyncio.to_thread(_extract_drawing_evidence, file_entries, 5)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process drawings: {str(e)}")

    if not evidence["visuals"] and not evidence["text_summary"]:
        return {"_success": False, "_error": "Could not read any pages or images from the uploaded drawings."}

    prompt = f"""You are a senior UAE Quantity Surveyor and Planning Engineer analyzing uploaded VILLA construction drawings (architectural, structural, site plans, area schedules).
Extract ONLY parameters you can determine WITH CONFIDENCE from the drawing text and attached visual sheets. Do NOT invent financial terms unless explicitly written on the drawings.

Return STRICT JSON:
{{
  "suggestions": {{ ... }},
  "confidence": "high|medium|low",
  "summaryEn": "1-2 concise sentences summarizing what you detected on the drawings",
  "summaryAr": "ملخص قصير من جملة أو جملتين بالعربية لما تم رصده في المخططات"
}}

Allowed keys inside "suggestions" (OMIT any key you cannot determine):
- villaType: exact floor configuration from {", ".join(VALID_VILLA_TYPES)}. Carefully count Ground + Upper habitable floors (do NOT count Roof/Upper Roof parapet/stair penthouse as an extra floor!). For example, Ground + First Floor + Roof = "G+1".
- buaPerFloor: number (typical floor Built-Up Area in m²; if an Area Schedule shows Ground Floor + First Floor BUA, compute the average typical floor BUA in m² — convert sq.ft to m² by dividing by 10.7639 if areas are in sq.ft!).
- basementArea: number (m², only if a basement exists).
- mezzanineArea: number (m², only if a mezzanine exists).
- foundationType: "isolated" (isolated/pad footings + tie beams/ground beams) OR "raft" (raft/mat foundation), based on the structural foundation layout.
- hasPool: boolean (true ONLY if a swimming pool is shown on the site/ground plan or mentioned in schedules).
- hasRoofGarden: boolean (true ONLY if a roof garden/landscaped roof terrace is shown).
- hasBoundaryWall: boolean (true if a compound/boundary wall, fence, or gate is shown or noted).
- hasExternalLandscape: boolean (true if external paving, interlocking, driveway, garden, or landscaping is shown).
- hasDemolition: boolean (true ONLY if existing structure demolition is explicitly noted).
- complexityFactor: 0.8 (simple boxy villa), 1.0 (standard UAE villa), or 1.2 (luxury/complex geometry, curved slabs, double-height volumes, extensive stone cladding).
- projectName, plotNumber, clientName, consultantName: string (from title block if readable).
- location: one of {", ".join(VALID_EMIRATES)} (from title block / municipality stamp such as DM=Dubai, ADM=Abu Dhabi, Sharjah Municipality=Sharjah, etc.).

EXTRACTED DRAWING TEXT ACROSS ALL {evidence['total_pages']} PAGES:
{evidence['text_summary'] or '(Scanned/image drawings — inspect the attached visual sheets carefully.)'}"""

    from google.genai import types

    contents: Any = [prompt]
    for _, label, img_bytes, mime in evidence["visuals"]:
        contents.append(f"\n--- Drawing Sheet: {label} ---")
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    parsed, err = await _run_gemini_json(contents, timeout_s=35.0)
    if err or not parsed:
        return {"_success": False, "_error": err or "AI drawing analysis failed."}

    sanitized = _sanitize_prefill(parsed)
    return {
        "_success": True,
        "suggestions": sanitized,
        "confidence": parsed.get("confidence", "medium"),
        "summaryEn": parsed.get("summaryEn") or parsed.get("notes") or "",
        "summaryAr": parsed.get("summaryAr") or "",
        "totalPages": evidence["total_pages"],
        "visualPagesAnalyzed": evidence["visual_count"],
    }
