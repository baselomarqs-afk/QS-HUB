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
    raw = await _ask_ai_with_retry(image_path, ELEVATION_PROMPT, key_manager)
    from workflow.step3_extract import parse_json
    return parse_json(raw)
