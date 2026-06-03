import json
import logging
from utils.key_manager import KeyManager

logger = logging.getLogger(__name__)

# Prompt strictly focused on counting doors and windows
OPENINGS_PROMPT = """This is a floor plan of a UAE villa. Your ONLY task is to count doors and windows. DO NOT attempt to read room dimensions or measure wall lengths. Focus 100% of your visual attention on finding door swing arcs, sliding door symbols, and window lines.

To ensure 100% accuracy, you MUST scan the drawing ROOM BY ROOM.
List EVERY room/space in the "rooms" array:
- "name": room name (Living, Bedroom, Bathroom, Kitchen, Majlis, Terrace, WC, Laundry …)
- "doors_count": count the doors (swing arcs/sliding symbols) for THIS specific room.
- "windows_count": count the windows on the external walls of THIS specific room.

Return ONLY this JSON (no markdown):
{"rooms":[{"name":"Living","doors_count":2,"windows_count":1}],
 "confidence":"high|medium|low","notes":""}"""

async def extract_openings_data(image_path: str, key_manager: KeyManager = None) -> dict:
    from workflow.step3_extract import _ask_ai_with_retry
    raw = await _ask_ai_with_retry(image_path, OPENINGS_PROMPT, key_manager)
    from workflow.step3_extract import parse_json
    return parse_json(raw)
