"""
كشف مقياس الرسم من scale bar
الأولوية: 1) نص مثل "1:100" 2) scale bar رسومي
"""
import cv2
import numpy as np
import re
from typing import Optional, Tuple


def detect_scale_from_text(page_array: np.ndarray) -> Optional[float]:
    """
    يبحث عن نص مثل "1:100" أو "SCALE 1:200" في الصورة باستخدام OCR
    Returns: pixels_per_meter أو None لو ما لقى
    """
    try:
        from pdf_engine.ocr_engine import extract_all_text, detect_scale_text_ocr
        texts = extract_all_text(page_array)
        scale_text = detect_scale_text_ocr(texts)
        if scale_text:
            return calculate_ppm(scale_text)
    except Exception as e:
        print(f"[Scale OCR Error] {e}")
    return None


def detect_scale_bar_visual(page_array: np.ndarray) -> Optional[Tuple[float, dict]]:
    """
    يحاول يكشف الـ scale bar البصري في المخطط
    يدور على خط أفقي مع نص أرقام بجانبه
    Returns: (pixels_per_meter, debug_info) أو None
    """
    gray = cv2.cvtColor(page_array, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Search in bottom 20% of page (where scale bars usually are)
    bottom_region = gray[int(h * 0.80):, :]

    # Detect horizontal lines (potential scale bars)
    edges = cv2.Canny(bottom_region, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi/180,
        threshold=80,
        minLineLength=int(w * 0.05),
        maxLineGap=10
    )

    if lines is None:
        return None

    # Find longest horizontal line — likely the scale bar
    best_line = None
    best_length = 0

    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Check if horizontal (angle < 5 degrees)
        if abs(y2 - y1) < 5:
            length = abs(x2 - x1)
            if length > best_length:
                best_length = length
                best_line = (x1, y1, x2, y2)

    if best_line is None or best_length < 50:
        return None

    debug = {
        "line": best_line,
        "pixel_length": best_length,
        "region": "bottom_20_percent"
    }

    # Without OCR we can't know the real-world length
    # Return pixel length and let user confirm
    return (best_length, debug)


def calculate_ppm(scale_text: str, bar_pixel_length: float = None) -> Optional[float]:
    """
    يحسب pixels per meter من نص المقياس
    scale_text: مثل "1:100" أو "1:200"
    bar_pixel_length: طول الـ scale bar بالبكسل (لو متاح)

    Returns: pixels_per_meter
    """
    # Parse scale ratio like 1:100
    match = re.search(r'1\s*[:/]\s*(\d+)', scale_text)
    if not match:
        return None

    ratio = int(match.group(1))  # e.g., 100 from "1:100"

    if bar_pixel_length and bar_pixel_length > 0:
        # If we know bar represents e.g. 1m at 1:100
        # pixels_per_meter = bar_pixel_length (if bar = 1m in drawing)
        # More commonly bar = some round number like 5m
        # This will be refined in Prompt 5 with OCR
        pixels_per_meter = bar_pixel_length  # placeholder
        return pixels_per_meter

    # Fallback: estimate from DPI and scale ratio
    # At 150 DPI: 1 inch = 150 pixels = 25.4mm real
    # At scale 1:100: 25.4mm drawing = 2540mm real = 2.54m
    # pixels_per_meter = 150 / (25.4 * ratio / 1000)
    dpi = 150
    pixels_per_mm_drawing = dpi / 25.4
    pixels_per_meter = (pixels_per_mm_drawing * 1000) / ratio

    return round(pixels_per_meter, 4)


def manual_scale_override(known_distance_pixels: float, known_distance_meters: float) -> float:
    """
    يحسب pixels per meter من قياس يدوي معروف
    المستخدم يختار نقطتين على المخطط ويدخل البعد الحقيقي
    """
    if known_distance_meters <= 0 or known_distance_pixels <= 0:
        return 0.0
    return round(known_distance_pixels / known_distance_meters, 4)
