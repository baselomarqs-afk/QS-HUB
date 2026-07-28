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
        pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=True)
        img  = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, (0, 0), img)
        arr  = np.array(bg.convert("RGB"))[:, :, ::-1].copy()
        pages.append(arr)
    doc.close()
    return pages


def fast_save_pdf_pages(pdf_bytes: bytes, project_id: int, prefix: str, start_idx: int) -> int:
    """
    High-speed PDF image extractor with optimized compression.
    Renders pages at smart DPI, caps at 1600px max dimension, and saves as
    JPEG quality=95 — reducing file size from ~6MB (PNG) to ~250KB (JPEG)
    while retaining full readability for AI extraction.
    Returns the number of pages processed.
    """
    from utils.storage import save_raw_image_to_cache

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)

    for page_num in range(page_count):
        page = doc[page_num]

        # Smart DPI: render at 100 DPI for decent quality, then cap at 1600px
        dpi = 100
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)

        # Cap longest dimension at 1600px to keep files tiny
        w, h = pix.width, pix.height
        if max(w, h) > 1600:
            ratio = 1600 / max(w, h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            # Use PIL for high-quality downscale (LANCZOS)
            pil_img = Image.frombytes("RGB", (w, h), pix.samples)
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
        else:
            pil_img = Image.frombytes("RGB", (w, h), pix.samples)

        # Save as JPEG quality=95 (lossless-like, ~250KB vs ~6MB PNG)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=95, optimize=True)
        jpg_bytes = buf.getvalue()

        global_idx = start_idx + page_num
        filename = f"{prefix}_page_{global_idx}.jpg"
        save_raw_image_to_cache(project_id, filename, jpg_bytes, format="JPEG")

    doc.close()
    return page_count


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
        if page_type == "schedules" and score > 0:
            score += 5
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
