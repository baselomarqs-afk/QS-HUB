import json
import logging
from utils.key_manager import KeyManager

logger = logging.getLogger(__name__)

# Prompt strictly focused on tracing wall lengths
WALL_PROMPT = """This is a floor plan of a UAE villa. Your ONLY task is to estimate the total length of INTERNAL partition walls AND the total length of EXTERNAL walls on this floor. DO NOT attempt to read room dimensions or count doors. Focus 100% of your attention on tracing wall lines and dimension lines.

Read every dimension line shown on the plan. Trace each wall segment (don't double-count where two walls meet at a corner — count each segment once).

- "int_walls_10cm_m" / "int_walls_20cm_m": total length (METRES) of the INTERNAL walls BY THICKNESS, read from the plan. 10 cm (100 mm) = thin partitions (around bathrooms/WCs, closets/dressing, light dividers); 20 cm (200 mm) = the main internal walls between rooms. Read the wall line thickness / any wall-type note. If you truly cannot tell them apart, return the total sum under "int_walls_20cm_m" and 0 for 10cm.

Return ONLY this JSON (no markdown):
{
  "int_walls_10cm_m": 0.0,
  "int_walls_20cm_m": 0.0,
  "confidence":"high|medium|low","notes":""
}"""

async def extract_wall_data(image_path: str, key_manager: KeyManager = None) -> dict:
    from workflow.step3_extract import _ask_ai_with_retry
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    raw = await _ask_ai_with_retry(img_bytes, WALL_PROMPT, key_manager)
    from workflow.step3_extract import parse_json
    return parse_json(raw)
