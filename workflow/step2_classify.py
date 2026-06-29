"""
STEP 2 — Classify Pages
AI reads each page title/text and assigns drawing type
User can correct any misclassification
"""
import pandas as pd
import os, io, re, json
from pdf_engine.smart_classifier import classify_all_pages, PAGE_ITEMS_MAP
from pdf_engine.pdf_loader import page_to_pil
from workflow.workflow_state import mark_step_done

# Candidate types per PDF kind — used by the AI-vision refiner
_STRUCT_TYPES = ["foundations", "tie_beam", "column_layout", "upper_columns", "neck_columns",
                 "columns_1f", "columns_2f", "columns_roof",
                 "slab_1st", "slab_2nd", "roof_slab"]
_ARCH_TYPES   = ["ground_floor_plan", "first_floor_plan", "second_floor_plan",
                 "roof_floor_plan", "elevations", "setting_out", "schedules"]


def _ai_classify(page_arr, pdf_type: str):
    """Classify ONE page by vision when keyword matching is unsure. Returns a
    PAGE_ITEMS_MAP key or None."""
    from utils.key_manager import get_key_manager
    mgr = get_key_manager()
    api_key, current_model = mgr.get_key_and_model()
    if not api_key or api_key == "NO_API_KEY_FOUND":
        return None
    choices = _STRUCT_TYPES if pdf_type == "structural" else _ARCH_TYPES
    try:
        from google import genai
        from google.genai import types
        import time
        import io as _io

        pil_img = page_to_pil(page_arr)
        buf = _io.BytesIO()
        pil_img.save(buf, format="PNG")
        img = buf.getvalue()
        prompt = (
            f"This is a construction drawing. Classify it as one of: {choices}. "
            "Reply ONLY with valid JSON: {\"type\": \"<chosen_type>\"}"
        )

        for attempt in range(5):
            api_key, current_model = mgr.get_key_and_model()
            if not api_key or api_key == "NO_API_KEY_FOUND":
                return None

            try:
                client = genai.Client(api_key=api_key, http_options={'timeout': 60})
                resp = client.models.generate_content(
                    model=current_model,
                    contents=[types.Part.from_bytes(data=img, mime_type="image/png"), prompt])
                raw = re.sub(r"```json|```", "", resp.text).strip()
                result = json.loads(raw).get("type")
                return result if result in PAGE_ITEMS_MAP else None
            except Exception as e:
                last_err = str(e)
                if any(code in last_err for code in ("429", "RESOURCE_EXHAUSTED", "quota")):
                    mgr.mark_rate_limited(api_key, current_model)
                    continue
                time.sleep(2)

        return None
    except Exception:
        return None




def _classify_single(text: str, pdf_type: str) -> dict:
    from pdf_engine.smart_classifier import PAGE_ITEMS_MAP
    text_lower = text.lower()
    scores = {}
    for ptype, config in PAGE_ITEMS_MAP.items():
        score = sum(1 for kw in config.get("drawing_keywords", []) if kw.lower() in text_lower)
        scores[ptype] = score
    best  = max(scores, key=scores.get)
    score = scores[best]
    return {
        "detected_type": best if score > 0 else "unknown",
        "confidence": "high" if score >= 2 else "medium" if score == 1 else "low",
        "items": PAGE_ITEMS_MAP.get(best, {}).get("extract_items", []) if score > 0 else [],
    }
