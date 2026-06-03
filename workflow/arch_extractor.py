import json
import logging
from utils.key_manager import KeyManager

logger = logging.getLogger(__name__)

# Prompt strictly focused on architectural layout (Rooms, Areas, Dimensions)
ARCH_PROMPT = """This is a floor plan of a UAE villa. Your ONLY task is to extract room dimensions, floor area, and overall dimensions. DO NOT attempt to count doors, windows, or measure walls. Focus 100% of your attention on reading text labels for room sizes and dimension lines.

Villa plans rarely write the room AREA, but they DO show each room's name and its DIMENSIONS (e.g. "5.00 x 4.00").
READ THE DIMENSIONS from the dimension lines or text — do not guess.

List EVERY room/space in the "rooms" array:
- "name": room name (Living, Bedroom, Bathroom, Kitchen, Majlis, Terrace, WC, Laundry …)
- "length_m","width_m": the room size from its dimension labels (METRES) — REQUIRED
- "area_m2": only if an area is explicitly printed (else null)

Also read the overall dimension lines:
- "overall_length_m","overall_width_m": building outer dimensions (METRES)
- "balcony_terrace_area_m2": open balcony + terrace area if shown (else null)
- "floor_height_m": floor-to-floor or floor-to-ceiling height if shown anywhere on the plan or in a note/section (e.g. 3.2, 4.0, 4.6) — in METRES. null if not found.

Return ONLY this JSON (no markdown):
{"rooms":[{"name":"Living","length_m":5.0,"width_m":4.0,"area_m2":null}],
 "overall_length_m":null,"overall_width_m":null,"balcony_terrace_area_m2":null,
 "floor_height_m":null,
 "confidence":"high|medium|low","notes":""}"""

async def extract_arch_data(image_path: str, key_manager: KeyManager = None) -> dict:
    from workflow.step3_extract import _ask_ai_with_retry
    raw = await _ask_ai_with_retry(image_path, ARCH_PROMPT, key_manager)
    from workflow.step3_extract import parse_json
    return parse_json(raw)
