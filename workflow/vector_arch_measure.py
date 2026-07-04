import sys
import os
import math
import fitz
from collections import defaultdict
import re

sys.path.insert(0, os.path.dirname(__file__))

def _pt_to_m(scale_ratio: int) -> float:
    return (25.4 / 72.0) * scale_ratio / 1000.0

def detect_page_scale(page) -> int:
    txt = page.get_text("text")
    ratios = [int(m) for m in re.findall(r"1\s*[:/]\s*(\d{2,3})", txt)]
    if not ratios: return 100
    if 100 in ratios: return 100
    return max(ratios)

def _is_valid_segment(L_m: float) -> bool:
    return 0.3 <= L_m <= 30.0

def _orient(x1, y1, x2, y2) -> str:
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    if dx > dy * 3: return "H"
    if dy > dx * 3: return "V"
    return "O"

def _merge_intervals(intervals):
    intervals.sort()
    m = []
    for lo, hi in intervals:
        if m and lo <= m[-1][1] + 1.0:
            m[-1][1] = max(m[-1][1], hi)
        else:
            m.append([lo, hi])
    return m

def extract_arch_vectors(pdf_path: str, page_index: int, scale_ratio: int = None) -> dict:
    """
    Extracts mathematical lengths of walls by finding PARALLEL LINE PAIRS spaced by wall thickness.
    Extracts the external perimeter using the Bounding Box of major architectural lines.
    """
    doc = fitz.open(pdf_path)
    if page_index >= len(doc):
        doc.close()
        return {}
    page = doc[page_index]
    ratio = scale_ratio or detect_page_scale(page)
    pt_to_m = _pt_to_m(ratio)

    # Collect every straight edge together with its stroke line-weight. Walls are
    # drawn heavier than furniture / fixtures / hatching / dimension lines, so the
    # weight lets us keep wall geometry and drop the rest — which is what used to
    # inflate the wall length several-fold.
    raw = []  # (x1, y1, x2, y2, width)
    for d in page.get_drawings():
        wt = float(d.get("width") or 0) or 0.0
        for it in d["items"]:
            if it[0] == "l":
                raw.append((it[1].x, it[1].y, it[2].x, it[2].y, wt))
            elif it[0] == "re":
                r = it[1]
                raw.extend([
                    (r.x0, r.y0, r.x1, r.y0, wt),
                    (r.x1, r.y0, r.x1, r.y1, wt),
                    (r.x1, r.y1, r.x0, r.y1, wt),
                    (r.x0, r.y1, r.x0, r.y0, wt),
                ])
    doc.close()

    # Line-weight filter: keep only the heavier (wall-weight) lines — but ONLY
    # when there is a clear weight distinction AND enough lines survive, otherwise
    # fall back to using everything (never risk under-counting walls).
    widths = sorted(w for *_ , w in raw if w > 0)
    segments = [(a, b, cc, d2) for a, b, cc, d2, _w in raw]
    if len(widths) >= 12:
        thr = widths[len(widths) // 2]  # median weight
        if thr > 0:
            heavy = [(a, b, cc, d2) for a, b, cc, d2, w in raw if w >= thr]
            if len(heavy) >= 8:
                segments = heavy

    h_lines = defaultdict(list)
    v_lines = defaultdict(list)
    
    # Bounding box of valid segments
    min_x, max_x, min_y, max_y = float('inf'), float('-inf'), float('inf'), float('-inf')

    for x1, y1, x2, y2 in segments:
        L_m = math.hypot(x2 - x1, y2 - y1) * pt_to_m
        if not _is_valid_segment(L_m):
            continue
            
        ori = _orient(x1, y1, x2, y2)
        if ori == "H":
            y = round((y1 + y2) / 2)
            lo, hi = min(x1, x2), max(x1, x2)
            h_lines[y].append([lo, hi])
            min_x, max_x = min(min_x, lo), max(max_x, hi)
            min_y, max_y = min(min_y, y), max(max_y, y)
        elif ori == "V":
            x = round((x1 + x2) / 2)
            lo, hi = min(y1, y2), max(y1, y2)
            v_lines[x].append([lo, hi])
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, lo), max(max_y, hi)

    # Calculate actual Bounding Box perimeter (assuming the main lines represent the building)
    # If the page had no lines, default to 0
    if min_x == float('inf'):
        math_ext_perimeter_m = 0.0
    else:
        width_m = (max_x - min_x) * pt_to_m
        height_m = (max_y - min_y) * pt_to_m
        math_ext_perimeter_m = (width_m + height_m) * 2

    # Find parallel pairs (Wall thickness detection)
    # 20cm wall ~ 0.2m / pt_to_m points
    tol_20cm_pts = 0.20 / pt_to_m
    tol_10cm_pts = 0.10 / pt_to_m
    
    def calculate_wall_lengths(line_dict, target_gap_pts):
        total_wall_len_pts = 0.0
        coords = sorted(line_dict.keys())
        for i, c1 in enumerate(coords):
            # merge intervals on this coordinate
            ivs1 = _merge_intervals(line_dict[c1])
            # look ahead for parallel coordinate
            for j in range(i+1, len(coords)):
                c2 = coords[j]
                gap = abs(c2 - c1)
                # Allow 15% tolerance for drawing inaccuracies
                if target_gap_pts * 0.85 <= gap <= target_gap_pts * 1.15:
                    ivs2 = _merge_intervals(line_dict[c2])
                    # calculate overlap
                    for l1, h1 in ivs1:
                        for l2, h2 in ivs2:
                            overlap_lo = max(l1, l2)
                            overlap_hi = min(h1, h2)
                            if overlap_hi > overlap_lo:
                                total_wall_len_pts += (overlap_hi - overlap_lo)
                elif gap > target_gap_pts * 1.15:
                    break
        return total_wall_len_pts

    h_20cm_len = calculate_wall_lengths(h_lines, tol_20cm_pts)
    v_20cm_len = calculate_wall_lengths(v_lines, tol_20cm_pts)
    h_10cm_len = calculate_wall_lengths(h_lines, tol_10cm_pts)
    v_10cm_len = calculate_wall_lengths(v_lines, tol_10cm_pts)

    math_int_walls_20cm_m = (h_20cm_len + v_20cm_len) * pt_to_m
    math_int_walls_10cm_m = (h_10cm_len + v_10cm_len) * pt_to_m

    return {
        "math_ext_perimeter_m": round(math_ext_perimeter_m, 2),
        "math_int_walls_20cm_m": round(math_int_walls_20cm_m, 2),
        "math_int_walls_10cm_m": round(math_int_walls_10cm_m, 2),
        "scale_used": f"1:{ratio}",
        "confidence": "high_if_vector"
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        res = extract_arch_vectors(sys.argv[1], int(sys.argv[2]) - 1)
        print(res)
