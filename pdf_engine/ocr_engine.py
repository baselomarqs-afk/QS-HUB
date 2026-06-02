"""
استخراج النصوص والأرقام من المخططات باستخدام OCR
"""
try:
    import easyocr
except ImportError:
    easyocr = None
import numpy as np
import re
import cv2
from typing import List, Dict, Optional
from functools import lru_cache


@lru_cache(maxsize=1)
def get_ocr_reader():
    """
    يحمل نموذج OCR مرة واحدة فقط (cache)
    يدعم العربي والإنجليزي
    """
    return easyocr.Reader(['en', 'ar'], gpu=False)


def _preprocess_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    Denoise + local-contrast (CLAHE) so small/blurry dimension text on dense
    construction drawings becomes more legible. Keeps the SAME image dimensions,
    so the bbox coordinates OCR returns remain valid (no rescaling needed).
    """
    try:
        if img is None:
            return img
        g = img
        if len(g.shape) == 3:
            g = cv2.cvtColor(g, cv2.COLOR_BGR2GRAY)
        g = cv2.fastNlMeansDenoising(g, None, 7, 7, 21)
        g = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
        return g
    except Exception:
        return img


def extract_all_text(page_array: np.ndarray, preprocess: bool = True) -> List[Dict]:
    """
    يستخرج كل النص من الصورة
    Returns: list of {text, bbox, confidence}
    bbox format: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
    """
    reader = get_ocr_reader()
    img = _preprocess_for_ocr(page_array) if preprocess else page_array
    results = reader.readtext(img)

    extracted = []
    for bbox, text, confidence in results:
        if confidence > 0.3:  # filter low confidence
            extracted.append({
                "text":       text.strip(),
                "bbox":       bbox,
                "confidence": round(confidence, 3),
                "center_x":   int((bbox[0][0] + bbox[2][0]) / 2),
                "center_y":   int((bbox[0][1] + bbox[2][1]) / 2),
            })

    return extracted


def extract_dimensions(text_results: List[Dict]) -> List[Dict]:
    """
    يفلتر النتائج ويستخرج فقط الأرقام التي تمثل أبعاداً
    يبحث عن: أرقام عشرية، أرقام بوحدة m أو cm أو mm
    Returns: list of {value_meters, text, bbox, center_x, center_y}
    """
    dimension_pattern = re.compile(
        r"""
        (\d+\.?\d*)     # number (integer or decimal)
        \s*             # optional space
        (mm|cm|m)?      # optional unit — longest match first
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    dimensions = []

    for item in text_results:
        text = item["text"].strip()

        # Skip text that's clearly not a dimension
        if len(text) > 15:  # too long to be a dimension
            continue
        if re.search(r'[a-zA-Z]{3,}', text):  # has long words
            continue

        matches = dimension_pattern.findall(text)

        for num_str, unit in matches:
            try:
                value = float(num_str)

                # Convert to meters
                if unit.lower() == 'cm':
                    value_m = value / 100
                elif unit.lower() == 'mm':
                    value_m = value / 1000
                else:
                    # If no unit, check magnitude
                    if value > 100:   # likely mm
                        value_m = value / 1000
                    elif value > 20:  # likely cm
                        value_m = value / 100
                    else:             # likely meters
                        value_m = value

                # Filter unrealistic dimensions for villas (0.1m – 50m)
                if 0.1 <= value_m <= 50.0:
                    dimensions.append({
                        "value_meters":  round(value_m, 3),
                        "original_text": text,
                        "unit":          unit if unit else "m (assumed)",
                        "bbox":          item["bbox"],
                        "center_x":      item["center_x"],
                        "center_y":      item["center_y"],
                        "confidence":    item["confidence"],
                    })
            except ValueError:
                continue

    return dimensions


def extract_dimensions_from_plain_text(text: str) -> List[Dict]:
    """
    Extract dimensions directly from plain text (e.g. fitz-extracted PDF text).
    Returns same format as extract_dimensions() but without bbox/center fields.
    """
    dimension_pattern = re.compile(
        r'(\d+\.?\d*)\s*(mm|cm|m)?(?=\s|$|[,;\)])',
        re.IGNORECASE,
    )
    dims = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 30:
            continue
        if re.search(r'[a-zA-Z]{4,}', line):
            continue
        for num_str, unit in dimension_pattern.findall(line):
            try:
                value = float(num_str)
                unit_l = unit.lower()
                if unit_l == 'cm':
                    value_m = value / 100
                elif unit_l == 'mm':
                    value_m = value / 1000
                else:
                    if value > 100:
                        value_m = value / 1000
                    elif value > 20:
                        value_m = value / 100
                    else:
                        value_m = value
                value_m = round(value_m, 3)
                if 0.1 <= value_m <= 50.0 and value_m not in seen:
                    seen.add(value_m)
                    dims.append({
                        "value_meters":  value_m,
                        "original_text": line,
                        "unit":          unit if unit else "m (assumed)",
                        "bbox":          None,
                        "center_x":      0,
                        "center_y":      0,
                        "confidence":    0.85,
                    })
            except ValueError:
                continue
    return dims


def detect_scale_text_ocr(text_results: List[Dict]) -> Optional[str]:
    """
    يبحث عن نص المقياس مثل 1:100 أو SCALE 1:200
    """
    # Accept 1:100, 1 / 100, 1-100, and "SCALE 1:100" (case-insensitive)
    scale_pattern = re.compile(r'1\s*[:/\-]\s*\d{1,4}')

    for item in text_results:
        text = item["text"]
        if scale_pattern.search(text):
            return text

    return None


def draw_dimensions_on_image(
    page_array: np.ndarray,
    dimensions: List[Dict],
) -> np.ndarray:
    """
    يرسم الأبعاد المكتشفة على الصورة للمراجعة البصرية
    """
    img = page_array.copy()

    for dim in dimensions:
        bbox = dim["bbox"]
        x1, y1 = int(bbox[0][0]), int(bbox[0][1])
        x2, y2 = int(bbox[2][0]), int(bbox[2][1])

        # Draw green rectangle around detected dimension
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Add label
        label = f"{dim['value_meters']}m"
        cv2.putText(
            img, label,
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (0, 200, 0), 1,
        )

    return img
