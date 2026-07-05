import json
import logging
from utils.key_manager import KeyManager

logger = logging.getLogger(__name__)

ARCH_PROMPT = """This is a floor plan of a UAE villa. Your task is to extract the overall dimensions and the complete list of rooms.

First, identify the maximum bounding box of the building's physical footprint.
- "overall_length_m": The longest single dimension across the entire footprint (meters). Read the outermost dimension line that spans the whole building.
- "overall_width_m": The orthogonal longest dimension across the footprint (meters).
- "balcony_terrace_area_m2": Estimate the total area (sqm) of any external balconies or terraces.

Then, list EVERY room/space shown on the plan. For each room:
- "name": The exact name of the room (e.g. "Master Bedroom", "Kitchen", "Majlis").
- "length_m": Length of the room (meters) if stated.
- "width_m": Width of the room (meters) if stated.
- "area_m2": Area of the room if explicitly stated, otherwise estimate from L*W.

CRITICAL - WET ROOMS: You MUST include EVERY wet room, each with its length_m and
width_m: the KITCHEN, ALL bathrooms/baths (one per bedroom + guest), the W.C /
toilet, any powder room, the LAUNDRY / WASH room, and the PANTRY. These rooms
drive the waterproofing and wall-tiling quantities - if you skip any of them the
wet-area quantities come out wrong. Read each small room's dimension lines; do
NOT merge or omit small wet rooms.

Return ONLY this JSON (no markdown):
{
  "overall_length_m": 0.0,
  "overall_width_m": 0.0,
  "balcony_terrace_area_m2": 0.0,
  "rooms": [
    {"name": "", "length_m": 0.0, "width_m": 0.0, "area_m2": 0.0}
  ],
  "confidence":"high|medium|low","notes":""
}"""

async def extract_arch_data(image_path: str, key_manager: KeyManager = None) -> dict:
    from workflow.step3_extract import _ask_ai_with_retry
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    raw = await _ask_ai_with_retry(img_bytes, ARCH_PROMPT, key_manager)
    import re
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)
