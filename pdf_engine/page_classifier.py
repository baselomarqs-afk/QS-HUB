"""
يصنف صفحات المخطط: أساسات، معماري، إنشائي، تشطيبات
"""
import re
from typing import Optional


DRAWING_TYPES = {
    "foundation":     ["foundation", "footing", "أساس", "أساسات", "FOUND", "F-"],
    "structural":     ["structural", "str", "إنشائي", "BEAM", "COLUMN", "SLAB"],
    "architectural":  ["arch", "floor plan", "مخطط", "معماري", "GROUND", "FIRST", "SECOND", "ROOF"],
    "setting_out":    ["setting out", "site plan", "موقع", "SITE"],
    "elevation":      ["elevation", "واجهة", "ELEV"],
    "schedule":       ["schedule", "جدول", "DOOR", "WINDOW"],
}


def classify_page(page_text: str) -> str:
    """
    يصنف نوع صفحة المخطط بناءً على النص المستخرج
    Returns: foundation | structural | architectural | setting_out | elevation | schedule | unknown
    """
    text_lower = page_text.lower()

    scores = {}
    for dtype, keywords in DRAWING_TYPES.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[dtype] = score

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"
