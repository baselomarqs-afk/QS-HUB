"""
Measure architectural bounds geometrically from vector PDFs.
This acts as a deterministic fallback to AI extraction for Overall Length, Width, and Perimeter.
"""
import fitz
import math
import logging

logger = logging.getLogger(__name__)

def detect_page_scale(page) -> int:
    import re
    txt = page.get_text("text")
    ratios = [int(m) for m in re.findall(r"1\s*[:/]\s*(\d{2,3})", txt)]
    if not ratios:
        return 100
    if 100 in ratios:
        return 100
    return max(ratios)

def measure_architectural_bounds(pdf_path: str, page_index: int) -> dict:
    """
    Extracts the maximum bounding box of the actual drawing vectors.
    Returns: { "longest_length_m", "longest_width_m", "external_perimeter_m" }
    """
    try:
        doc = fitz.open(pdf_path)
        if page_index >= len(doc):
            return {}
            
        page = doc[page_index]
        scale = detect_page_scale(page)
        pt_to_m = (25.4 / 72.0) * scale / 1000.0

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        found_lines = False

        # Get the page mediabox to filter out border/title block lines
        # Usually, the title block is within 5-10% of the page edges.
        w, h = page.rect.width, page.rect.height
        margin_x = w * 0.08
        margin_y = h * 0.08

        for d in page.get_drawings():
            for it in d["items"]:
                pts = []
                if it[0] == "l":
                    pts = [it[1], it[2]]
                elif it[0] == "re":
                    r = it[1]
                    pts = [fitz.Point(r.x0, r.y0), fitz.Point(r.x1, r.y1)]
                elif it[0] == "c":
                    pts = [it[1], it[2], it[3], it[4]]
                
                for p in pts:
                    # Ignore lines that are part of the title block (too close to edges)
                    if p.x > margin_x and p.x < (w - margin_x) and p.y > margin_y and p.y < (h - margin_y):
                        min_x = min(min_x, p.x)
                        min_y = min(min_y, p.y)
                        max_x = max(max_x, p.x)
                        max_y = max(max_y, p.y)
                        found_lines = True

        doc.close()

        if not found_lines:
            return {}

        length_m = abs(max_x - min_x) * pt_to_m
        width_m = abs(max_y - min_y) * pt_to_m

        # Sanity check: if dimensions are ridiculously small or large, ignore them
        if length_m < 2.0 or width_m < 2.0 or length_m > 150.0:
            return {}

        return {
            "longest_length_m": round(max(length_m, width_m), 2),
            "longest_width_m": round(min(length_m, width_m), 2),
            "external_perimeter_m": round(2 * (length_m + width_m), 2),
            "_vector_measured": True
        }
    except Exception as e:
        logger.error(f"Failed to measure vector bounds: {e}")
        return {}
