import json
import logging
from utils.key_manager import KeyManager

logger = logging.getLogger(__name__)

# Prompt strictly focused on extracting height levels from Elevations and Sections
ELEVATION_PROMPT = """This is an Architectural Elevation or Section drawing of a UAE villa. Your ONLY task is to extract the vertical heights (levels) of the floors and the building. DO NOT attempt to read room dimensions or count items.

Look for level markers, elevation tags, or vertical dimension lines (e.g. FFL, SSL, Top of Parapet).
Extract the following heights in METRES. Do not guess. If you cannot clearly see the dimension for a specific floor, return null for that field.

Return ONLY this JSON (no markdown, no explanations):
{
  "gf_height_m": 4.0,           // Floor-to-floor height of Ground Floor (e.g. difference between 1st Floor FFL and Ground FFL)
  "f1_height_m": 4.0,           // Floor-to-floor height of First Floor
  "total_villa_height_m": 9.5,  // Total height from Ground Level to the absolute highest point (e.g. Top of Parapet)
  "parapet_height_m": 1.2,      // Height of the roof parapet wall
  "confidence": "high|medium|low",
  "notes": ""
}"""

async def extract_elevation_data(image_path: str, key_manager: KeyManager = None) -> dict:
    from workflow.step3_extract import _ask_ai_with_retry
    from pdf_engine.ocr_engine import extract_all_text, extract_dimensions
    import cv2
    
    # 1. OCR Extraction of physical dimensions
    img_cv = cv2.imread(image_path)
    if img_cv is not None:
        extracted_text = extract_all_text(img_cv, preprocess=True)
        dims = extract_dimensions(extracted_text)
        # Get unique dimension values
        dim_values = list(set([str(d['value_meters']) for d in dims]))
    else:
        dim_values = []
        
    prompt = ELEVATION_PROMPT
    if dim_values:
        ocr_string = ", ".join(dim_values)
        prompt += f"\n\nCRITICAL INSTRUCTION: I have mathematically extracted the following numeric dimensions (in meters) from the image using OCR: [{ocr_string}]. You MUST select the floor heights ONLY from these exact numbers. DO NOT hallucinate or invent any numbers that are not in this list."

    with open(image_path, "rb") as f:
        img_bytes = f.read()
    raw = await _ask_ai_with_retry(img_bytes, prompt, key_manager)
    from _pdf_utils import parse_json
    return parse_json(raw)
