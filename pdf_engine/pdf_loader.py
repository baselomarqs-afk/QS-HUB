"""
تحميل ومعالجة عدة ملفات PDF
"""
import fitz
import numpy as np
from PIL import Image
import io
from typing import List


def load_pdf_pages(pdf_bytes: bytes, dpi: int = 150) -> List[np.ndarray]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    
    # Dynamic DPI reduction to prevent Out-Of-Memory (OOM) on 512MB free servers
    page_count = len(doc)
    if page_count > 10:
        dpi = min(dpi, 50)
    elif page_count > 3:
        dpi = min(dpi, 72)
    else:
        dpi = min(dpi, 100)
        
    for page_num in range(page_count):
        page = doc[page_num]
        mat  = fitz.Matrix(dpi / 72, dpi / 72)
        pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img  = Image.open(io.BytesIO(pix.tobytes("png")))
        arr  = np.array(img)[:, :, ::-1].copy()
        pages.append(arr)
    doc.close()
    return pages


def extract_page_text(pdf_bytes: bytes) -> List[str]:
    """يستخرج النص المباشر من كل صفحة PDF بدون OCR — أسرع للتصنيف الأولي"""
    doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
    texts = []
    for page in doc:
        texts.append(page.get_text().strip())
    doc.close()
    return texts


def classify_page_by_text(page_text: str, page_image: np.ndarray = None) -> str:
    """يصنف الصفحة بناءً على النص — يرجع مفتاح PAGE_ITEMS_MAP"""
    from pdf_engine.smart_classifier import PAGE_ITEMS_MAP

    text_lower = page_text.lower()
    scores     = {}
    for page_type, config in PAGE_ITEMS_MAP.items():
        score = sum(1 for kw in config["drawing_keywords"] if kw.lower() in text_lower)
        scores[page_type] = score

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def page_to_pil(page_array: np.ndarray) -> Image.Image:
    return Image.fromarray(page_array[:, :, ::-1].copy())


def get_page_count(pdf_bytes: bytes) -> int:
    doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count
