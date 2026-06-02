"""
يربط الأبعاد المستخرجة بالعناصر الموجودة في المخطط
"""
import numpy as np
from typing import List, Dict, Tuple, Optional


def find_nearest_dimension(
    element_center: Tuple[float, float],
    dimensions: List[Dict],
    max_distance_pixels: float = 200.0,
) -> Optional[Dict]:
    """
    يجد أقرب بُعد لعنصر معين
    element_center: (x, y) مركز العنصر بالبكسل
    """
    ex, ey = element_center
    best = None
    best_dist = float('inf')

    for dim in dimensions:
        dx = dim["center_x"] - ex
        dy = dim["center_y"] - ey
        dist = (dx**2 + dy**2) ** 0.5

        if dist < best_dist and dist < max_distance_pixels:
            best_dist = dist
            best = dim

    return best


def group_dimensions_by_direction(dimensions: List[Dict]) -> Dict:
    """
    يصنف الأبعاد إلى أفقية وعمودية
    """
    horizontal = []
    vertical   = []

    for dim in dimensions:
        bbox   = dim["bbox"]
        width  = abs(bbox[2][0] - bbox[0][0])
        height = abs(bbox[2][1] - bbox[0][1])

        if width >= height:
            horizontal.append(dim)
        else:
            vertical.append(dim)

    return {"horizontal": horizontal, "vertical": vertical}


def extract_room_dimensions(
    dimensions: List[Dict],
    pixels_per_meter: float,
) -> List[Dict]:
    """
    يحاول يستخرج أبعاد الغرف (أكبر الأبعاد الأفقية والعمودية)
    """
    if pixels_per_meter <= 0:
        return []

    grouped = group_dimensions_by_direction(dimensions)
    rooms   = []

    # Sort by value to find major dimensions
    h_sorted = sorted(grouped["horizontal"], key=lambda d: d["value_meters"], reverse=True)
    v_sorted = sorted(grouped["vertical"],   key=lambda d: d["value_meters"], reverse=True)

    # Pair horizontal + vertical dimensions that are close together
    used_h = set()
    used_v = set()

    for i, hdim in enumerate(h_sorted[:10]):  # top 10 horizontal
        if i in used_h:
            continue
        for j, vdim in enumerate(v_sorted[:10]):
            if j in used_v:
                continue

            # Check if they're in the same region
            hx, hy = hdim["center_x"], hdim["center_y"]
            vx, vy = vdim["center_x"], vdim["center_y"]
            dist   = ((hx - vx)**2 + (hy - vy)**2) ** 0.5

            if dist < 300:  # within 300 pixels of each other
                rooms.append({
                    "width":    hdim["value_meters"],
                    "length":   vdim["value_meters"],
                    "area":     round(hdim["value_meters"] * vdim["value_meters"], 2),
                    "center_x": (hx + vx) / 2,
                    "center_y": (hy + vy) / 2,
                })
                used_h.add(i)
                used_v.add(j)
                break

    return rooms
