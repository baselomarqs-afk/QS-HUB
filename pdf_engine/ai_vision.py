"""
تحليل المخططات باستخدام AI Vision API مع ميزات التخزين المؤقت والـ Fallback المحلي
"""
import os
import json
import re
import io
import numpy as np
from PIL import Image
from typing import Dict, List, Optional
from google import genai
from google.genai import types
from utils.key_manager import get_key_manager
from utils.cache_manager import get_file_hash, get_cached_response, save_cached_response
from pdf_engine.element_detector import detect_columns, detect_walls, detect_rooms, calculate_detection_summary


MODEL = "gemini-3.1-flash-lite"

_PROMPT_TEMPLATE = """You are an expert QTO (Quantity Takeoff) engineer analyzing a UAE villa {drawing_type} drawing.
Drawing: {floor_name}
{scale_info}

Analyze this drawing carefully and extract ALL of the following data.
Respond ONLY with a valid JSON object. No explanation, no markdown fences, no extra text.

{{
  "floor_type": "ground|first|second|roof|foundation|structural",
  "drawing_confirmed": true,
  "total_floor_area_m2": <number or null>,
  "external_perimeter_m": <number or null>,
  "internal_walls_total_length_m": <number or null>,
  "wet_areas": {{
    "total_area_m2": <number or null>,
    "total_perimeter_m": <number or null>,
    "rooms": [
      {{"name": "bathroom", "area_m2": <number>, "perimeter_m": <number>}}
    ]
  }},
  "dry_area_m2": <number or null>,
  "dry_area_perimeter_m": <number or null>,
  "balcony_area_m2": <number or null>,
  "columns": [
    {{"width_m": <number>, "length_m": <number>, "count": <number>, "label": "C1"}}
  ],
  "beams": [
    {{"width_m": <number>, "depth_m": <number>, "length_m": <number>, "label": "B1"}}
  ],
  "slab_thickness_m": <number or null>,
  "foundations": [
    {{"width_m": <number>, "length_m": <number>, "depth_m": <number>, "count": <number>}}
  ],
  "tie_beam": {{
    "width_m": <number or null>,
    "depth_m": <number or null>,
    "total_length_m": <number or null>
  }},
  "doors": [
    {{"type": "main|room|bathroom", "width_m": <number>, "height_m": <number>, "count": <number>}}
  ],
  "windows": [
    {{"type": "standard|sliding|fixed", "width_m": <number>, "height_m": <number>, "count": <number>}}
  ],
  "floor_height_m": <number or null>,
  "notes": "<any important observations>",
  "confidence": "high|medium|low"
}}

If you cannot determine a value with reasonable confidence, use null.
Only include values you can actually see or reasonably infer from the drawing."""


def _page_to_png_bytes(page_array: np.ndarray) -> bytes:
    """Converts numpy BGR array to PNG bytes, resizing if needed."""
    rgb = page_array[:, :, ::-1].copy()
    pil_img = Image.fromarray(rgb)

    max_side = 2000
    w, h = pil_img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def local_fallback_takeoff(page_array: np.ndarray, floor_name: str, pixels_per_meter: float) -> Dict:
    """
    Local OpenCV + EasyOCR fallback takeoff if AI is unavailable.
    """
    ppm = pixels_per_meter if pixels_per_meter > 0 else 100.0  # Default scale fallback
    
    rooms = detect_rooms(page_array, ppm)
    walls = detect_walls(page_array, ppm)
    columns = detect_columns(page_array, ppm)
    
    summary = calculate_detection_summary(columns, walls, rooms)
    
    # Structure like AI output
    cols_formatted = []
    for size_str, count in summary["column_schedule"].items():
        try:
            w_m, h_m = map(float, size_str.split("x"))
            cols_formatted.append({
                "width_m": w_m,
                "length_m": h_m,
                "count": count,
                "label": "C_loc"
            })
        except Exception:
            pass
            
    return {
        "floor_type": "ground" if "ground" in floor_name.lower() else "first" if "first" in floor_name.lower() else "roof",
        "drawing_confirmed": True,
        "total_floor_area_m2": summary["total_area_m2"],
        "external_perimeter_m": summary["total_perim_m"],
        "internal_walls_total_length_m": summary["total_wall_m"],
        "wet_areas": {
            "total_area_m2": round(summary["total_area_m2"] * 0.15, 2),
            "total_perimeter_m": round(summary["total_perim_m"] * 0.15, 2),
            "rooms": [{"name": "bathroom_loc", "area_m2": round(summary["total_area_m2"] * 0.15, 2), "perimeter_m": round(summary["total_perim_m"] * 0.15, 2)}]
        },
        "dry_area_m2": round(summary["total_area_m2"] * 0.85, 2),
        "dry_area_perimeter_m": round(summary["total_perim_m"] * 0.85, 2),
        "balcony_area_m2": 0.0,
        "columns": cols_formatted,
        "beams": [],
        "slab_thickness_m": 0.20,
        "foundations": [],
        "tie_beam": {"width_m": None, "depth_m": None, "total_length_m": None},
        "doors": [],
        "windows": [],
        "floor_height_m": 3.2,
        "notes": "Calculated locally using OpenCV/EasyOCR local algorithms (AI Offline Fallback).",
        "confidence": "medium",
        "_api_success": False,
        "_local_fallback": True
    }


def analyze_drawing_page(
    page_array: np.ndarray,
    drawing_type: str = "architectural",
    floor_name: str = "Ground Floor",
    pixels_per_meter: float = 0.0,
    geometry_context: str = "",
) -> Dict:
    """
    Sends a drawing page to AI and extracts QTO data.
    Implements: Caching & OpenCV local fallback on API error/quota limits.
    """
    # 1. Check local cache first
    file_hash = get_file_hash(page_array)
    prompt_key = f"{drawing_type}_{floor_name}_{pixels_per_meter:.2f}"
    
    cached = get_cached_response(file_hash, prompt_key)
    if cached:
        try:
            result = json.loads(cached)
            result["_api_success"] = True
            result["_cached"] = True
            print(f"[Cache Hit] Returned cached QTO data for {floor_name} (Hash: {file_hash[:8]})")
            return result
        except Exception:
            pass

    manager = get_key_manager()
    api_key, model_name = manager.get_key_and_model()
    
    if not api_key:
        print("[No API Key] Falling back to local OpenCV takeoff.")
        return local_fallback_takeoff(page_array, floor_name, pixels_per_meter)

    client = genai.Client(api_key=api_key)

    scale_info = (
        f"Drawing scale: {pixels_per_meter:.1f} pixels per meter."
        if pixels_per_meter > 0
        else "Scale not provided — estimate from visible dimension labels."
    )

    prompt = _PROMPT_TEMPLATE.format(
        drawing_type=drawing_type,
        floor_name=floor_name,
        scale_info=scale_info,
    )

    # Give the model the deterministic vector measurements as grounding so it
    # reasons over real geometry, not only pixels (improves scale/size reading).
    if geometry_context:
        prompt = prompt + "\n\n" + geometry_context

    png_bytes = _page_to_png_bytes(page_array)

    raw_text = ""
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                types.Part.from_text(text=prompt),
            ],
        )

        raw_text = response.text.strip()

        # Strip any accidental markdown fences
        raw_text = re.sub(r"```json|```", "", raw_text).strip()

        result = json.loads(raw_text)
        result["_api_success"] = True
        result["_model"]       = MODEL
        result["_key_hint"]    = f"...{api_key[-6:]}"

        # Token usage
        usage = getattr(response, "usage_metadata", None)
        if usage:
            result["_input_tokens"]  = getattr(usage, "prompt_token_count", "?")
            result["_output_tokens"] = getattr(usage, "candidates_token_count", "?")

        # Save to local cache
        save_cached_response(file_hash, prompt_key, json.dumps(result, ensure_ascii=False))
        return result

    except json.JSONDecodeError as e:
        print(f"[JSON Decode Error] {e}. Raw response: {raw_text}. Falling back to local takeoff.")
        return local_fallback_takeoff(page_array, floor_name, pixels_per_meter)
    except Exception as e:
        err = str(e)
        print(f"[AI Exception] {err}. Falling back to local takeoff.")
        if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
            get_key_manager().mark_rate_limited(api_key, model_name)
        return local_fallback_takeoff(page_array, floor_name, pixels_per_meter)


def analyze_multiple_pages(
    pages: List[np.ndarray],
    page_assignments: Dict[int, str],
    pixels_per_meter: float,
) -> Dict[str, Dict]:
    """
    Analyzes multiple pages, one per assigned floor.
    page_assignments: {page_index: "Ground Floor|First Floor|..."}
    Returns: {floor_name: analysis_result}
    """
    results = {}
    for page_idx, floor_name in page_assignments.items():
        if page_idx < len(pages):
            results[floor_name] = analyze_drawing_page(
                pages[page_idx],
                floor_name=floor_name,
                pixels_per_meter=pixels_per_meter,
            )
    return results
