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
    if ratios:
        return 100 if 100 in ratios else max(ratios)
    try:
        from pdf_engine.vector_intelligence import calibrate_scale_from_dimensions
        cal = calibrate_scale_from_dimensions(page)
        if cal:
            return cal["ratio"]
    except Exception:
        pass
    return 100

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

        # Enhanced deterministic measures (line-weight-filtered bounds + real
        # closed-polygon area). Computed while the page is still open; any failure
        # silently leaves the raw bounding box as the fallback.
        filtered = None
        poly_area = None
        try:
            from pdf_engine.vector_intelligence import filtered_building_bounds, polygon_area_m2
            filtered = filtered_building_bounds(page, scale)
            poly_area = polygon_area_m2(page, scale)
        except Exception:
            pass

        doc.close()

        if not found_lines:
            return {}

        length_m = abs(max_x - min_x) * pt_to_m
        width_m = abs(max_y - min_y) * pt_to_m

        # Sanity check: if dimensions are ridiculously small or large, ignore them
        if length_m < 2.0 or width_m < 2.0 or length_m > 150.0:
            return {}

        bbox_L = round(max(length_m, width_m), 2)
        bbox_W = round(min(length_m, width_m), 2)
        bbox_perim = round(2 * (length_m + width_m), 2)

        # Prefer the wall-weight-filtered bounds (drops dimension/grid lines that
        # inflate a raw bounding box); confidence comes from how well the two
        # independent measures agree.
        out = {
            "longest_length_m": bbox_L,
            "longest_width_m": bbox_W,
            "external_perimeter_m": bbox_perim,
            "_vector_measured": True,
        }
        if filtered:
            try:
                from pdf_engine.vector_intelligence import reconcile
                rc = reconcile(filtered["external_perimeter_m"], bbox_perim)
                out["longest_length_m"] = filtered["longest_length_m"]
                out["longest_width_m"] = filtered["longest_width_m"]
                out["external_perimeter_m"] = filtered["external_perimeter_m"]
                out["_confidence"] = rc["confidence"]
            except Exception:
                pass
        if poly_area:
            out["gf_area"] = poly_area
            out["_polygon_area"] = poly_area
        return out
    except Exception as e:
        logger.error(f"Failed to measure vector bounds: {e}")
        return {}
