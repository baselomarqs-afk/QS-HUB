"""
كشف العناصر الإنشائية والمعمارية من المخططات
يستخدم OpenCV بدون AI — معالجة بصرية بحتة مع تحسين الفلترة وإزالة الشبكات
"""
import cv2
import numpy as np
from typing import List, Dict


def preprocess_drawing(page_array: np.ndarray) -> np.ndarray:
    """
    Preprocesses the drawing image:
    1. Converts to grayscale.
    2. Identifies if it is dark mode and normalizes it to a white background.
    3. Removes grid lines using morphological opening.
    4. Enhances high-contrast line features.
    """
    gray = cv2.cvtColor(page_array, cv2.COLOR_BGR2GRAY)
    
    # Check if background is dark (mean pixel value < 127)
    is_dark = np.mean(gray) < 127
    if is_dark:
        gray = cv2.bitwise_not(gray) # Invert to standard black-on-white layout
        
    h, w = gray.shape
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Morphological grid line detection (long thin grids)
    grid_h = max(int(h * 0.04), 10)
    grid_w = max(int(w * 0.04), 10)
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, grid_h))
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (grid_w, 1))
    
    ver_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, ver_kernel, iterations=1)
    hor_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, hor_kernel, iterations=1)
    
    # Combine grids
    grids = cv2.add(ver_lines, hor_lines)
    
    # Remove grids by setting grid pixels to background (white)
    cleaned = gray.copy()
    cleaned[grids > 200] = 255
    
    # Morphological closing to heal small text elements and drawing gaps
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
    
    return cleaned


def detect_columns(
    page_array: np.ndarray,
    pixels_per_meter: float,
    min_size_m: float = 0.20,
    max_size_m: float = 1.50,
) -> List[Dict]:
    """يكشف الأعمدة كمستطيلات صغيرة مملوءة في المخطط"""
    if pixels_per_meter <= 0:
        return []

    min_px = int(min_size_m * pixels_per_meter * 0.5)
    max_px = int(max_size_m * pixels_per_meter * 2.0)

    # Use preprocessed clean image
    gray = preprocess_drawing(page_array)
    _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    columns = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        if not (min_px <= w <= max_px and min_px <= h <= max_px):
            continue

        aspect = max(w, h) / max(min(w, h), 1)
        if aspect > 3.0:
            continue

        roi = binary[y:y+h, x:x+w]
        fill_ratio = np.sum(roi > 0) / (w * h)
        if fill_ratio < 0.60:
            continue

        columns.append({
            "x": x, "y": y, "w": w, "h": h,
            "width_m":  round(w / pixels_per_meter, 3),
            "height_m": round(h / pixels_per_meter, 3),
            "area_m2":  round((w / pixels_per_meter) * (h / pixels_per_meter), 4),
            "center_x": x + w // 2,
            "center_y": y + h // 2,
        })

    return columns


def detect_walls(page_array: np.ndarray, pixels_per_meter: float) -> List[Dict]:
    """يكشف الجدران كخطوط سميكة في المخطط بعد إزالة شبكة الإحداثيات"""
    if pixels_per_meter <= 0:
        return []

    # Use preprocessed clean image
    gray = preprocess_drawing(page_array)
    edges = cv2.Canny(gray, 50, 150)

    min_wall_length_px = int(0.5 * pixels_per_meter)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=100,
        minLineLength=min_wall_length_px,
        maxLineGap=20,
    )

    if lines is None:
        return []

    walls = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length_px = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        angle     = np.degrees(np.arctan2(abs(y2 - y1), abs(x2 - x1)))
        direction = "horizontal" if angle < 15 else "vertical" if angle > 75 else "diagonal"

        walls.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "length_m":  round(length_px / pixels_per_meter, 3),
            "direction": direction,
            "angle_deg": round(angle, 1),
        })

    return walls


def detect_rooms(page_array: np.ndarray, pixels_per_meter: float) -> List[Dict]:
    """يكشف الغرف كمناطق مغلقة في مخطط الطابق"""
    if pixels_per_meter <= 0:
        return []

    # Use preprocessed clean image
    gray = preprocess_drawing(page_array)
    kernel = np.ones((3, 3), np.uint8)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    dilated   = cv2.dilate(binary, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area_px = int((1.0 * pixels_per_meter) ** 2)
    max_area_px = int((30.0 * pixels_per_meter) ** 2)

    rooms = []
    for cnt in contours:
        area_px = cv2.contourArea(cnt)
        if not (min_area_px <= area_px <= max_area_px):
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        area_m2 = round(area_px / (pixels_per_meter ** 2), 2)
        perim_m = round(cv2.arcLength(cnt, True) / pixels_per_meter, 2)

        rooms.append({
            "x": x, "y": y, "w": w, "h": h,
            "area_m2":  area_m2,
            "perim_m":  perim_m,
            "width_m":  round(w / pixels_per_meter, 2),
            "height_m": round(h / pixels_per_meter, 2),
            "center_x": x + w // 2,
            "center_y": y + h // 2,
        })

    rooms.sort(key=lambda r: r["area_m2"], reverse=True)
    return rooms


def draw_detections(
    page_array: np.ndarray,
    columns:    List[Dict],
    walls:      List[Dict],
    rooms:      List[Dict],
) -> np.ndarray:
    """يرسم كل العناصر المكتشفة على الصورة"""
    img = page_array.copy()

    for room in rooms:
        cv2.rectangle(img, (room["x"], room["y"]),
                      (room["x"] + room["w"], room["y"] + room["h"]),
                      (255, 150, 0), 2)
        cv2.putText(img, f"{room['area_m2']}m2",
                    (room["x"] + 5, room["y"] + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)

    for wall in walls:
        cv2.line(img, (wall["x1"], wall["y1"]), (wall["x2"], wall["y2"]),
                 (0, 200, 0), 2)

    for col in columns:
        cv2.rectangle(img, (col["x"], col["y"]),
                      (col["x"] + col["w"], col["y"] + col["h"]),
                      (0, 0, 255), 3)
        cv2.putText(img, f"{col['width_m']}x{col['height_m']}",
                    (col["x"], col["y"] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)

    return img


def calculate_detection_summary(
    columns: List[Dict],
    walls:   List[Dict],
    rooms:   List[Dict],
) -> Dict:
    """يلخص نتائج الكشف في أرقام جاهزة للـ QTO engine"""
    total_wall_h = sum(w["length_m"] for w in walls if w["direction"] == "horizontal")
    total_wall_v = sum(w["length_m"] for w in walls if w["direction"] == "vertical")
    total_area   = sum(r["area_m2"] for r in rooms)
    total_perim  = sum(r["perim_m"] for r in rooms)

    col_sizes: Dict[str, int] = {}
    for col in columns:
        key = f"{col['width_m']}x{col['height_m']}"
        col_sizes[key] = col_sizes.get(key, 0) + 1

    return {
        "column_count":    len(columns),
        "column_schedule": col_sizes,
        "wall_h_total_m":  round(total_wall_h, 2),
        "wall_v_total_m":  round(total_wall_v, 2),
        "total_wall_m":    round(total_wall_h + total_wall_v, 2),
        "room_count":      len(rooms),
        "total_area_m2":   round(total_area, 2),
        "total_perim_m":   round(total_perim, 2),
        "rooms":           rooms,
    }
