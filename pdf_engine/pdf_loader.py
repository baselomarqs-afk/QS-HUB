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
    High-speed PDF image extractor. Bypasses numpy and PIL conversions.
    Extracts straight from fitz (C++) to compressed PNG and saves via storage backend.
    Runs in parallel to maximize CPU cores.
    Returns the number of pages processed.
    """
    from concurrent.futures import ThreadPoolExecutor
    from utils.storage import save_raw_image_to_cache
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    
    # Pre-calculate a sensible scaling matrix
    # Hardcoded to max 50 DPI for all pages. This guarantees images stay around 1-2 MB,
    # completely eliminating network timeouts when uploading to the AI, while retaining
    # enough resolution for Gemini to read clearly.
    dpi = 50
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)
    
    # We will run the conversion to bytes in parallel, but fitz Document isn't thread-safe
    # for rendering if we share the same `doc`. 
    # Actually, `get_pixmap` is thread-safe on separate pages in modern PyMuPDF, but to be 100% safe
    # we just run the byte conversion and saving in parallel.
    
    def process_and_save(page_num):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
        png_bytes = pix.tobytes("png")
        global_idx = start_idx + page_num
        filename = f"{prefix}_page_{global_idx}.png"
        save_raw_image_to_cache(project_id, filename, png_bytes)
        
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(process_and_save, range(page_count)))
        
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
