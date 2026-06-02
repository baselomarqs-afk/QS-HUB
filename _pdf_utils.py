"""
Shared PDF + AI utilities for the villa_qto extraction pipeline.

Features:
    - PDF page rendering with auto-rotation correction       [W4]
    - AI Vision wrapper with disk caching                [W1]
    - Hard failure on retry exhaustion (no silent None)      [W2]
    - Image preprocessing for OCR (greyscale + threshold)    [W3]
    - Strict, normalized token counting                      [W5]
    - fitz text extraction with OCR fallback                 [W5]
    - Scanned-vs-text PDF detection
    - Automatic API key rotation on 429 / RESOURCE_EXHAUSTED [KEY_ROT]
"""
import os, io, re, json, time, hashlib
from typing import Optional
import fitz
from PIL import Image, ImageOps, ImageFilter

from _qto_config import (
    AI_MODEL, AI_API_KEY, AI_RETRIES, AI_RETRY_WAIT_S,
    AI_CACHE_ENABLED, CACHE_DIR, get_logger,
)
from utils.key_manager import get_key_manager

log = get_logger("pdf_utils")


# ── AI client pool (one client per key) [KEY_ROT] ────────────────────────
_CLIENT_POOL: dict = {}   # api_key → genai.Client


def get_ai_client(api_key: str | None = None):
    """
    Returns a AI client for the given key.
    Builds a new client only the first time a key is seen;
    subsequent calls reuse the cached instance.
    """
    import google.genai as genai
    key = api_key or AI_API_KEY
    if not key:
        raise RuntimeError("No AI API key. Set GOOGLE_API_KEY env var or pass api_key.")
    if key not in _CLIENT_POOL:
        _CLIENT_POOL[key] = genai.Client(api_key=key)
    return _CLIENT_POOL[key]


# ── PDF rendering with auto-rotation [W4] ─────────────────────────────────────
def render_page(pdf_path: str, page_index: int, dpi: int = 220,
                crop_box: tuple[float, float, float, float] | None = None,
                auto_rotate: bool = True) -> Image.Image:
    """
    Render a single PDF page to a PIL Image.

    Args:
        pdf_path:    Path to PDF.
        page_index:  0-based page number.
        dpi:         Rendering DPI.
        crop_box:    Optional (x0, y0, x1, y1) AFTER rendering, in pixel coords.
        auto_rotate: If True, applies page.rotation (90/180/270) automatically so
                     the output image is upright. Default True.
    """
    doc  = fitz.open(pdf_path)
    page = doc[page_index]
    mat  = fitz.Matrix(dpi/72, dpi/72)
    # fitz handles rotation natively via matrix when get_pixmap is called normally.
    # For PDFs where the rotation flag is non-zero, fitz already orients correctly.
    pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img  = Image.open(io.BytesIO(pix.tobytes("png")))
    rot  = page.rotation
    doc.close()

    # Belt-and-suspenders: if rotation flag exists but Pixmap ignored it
    # (very old scans), apply manually
    if auto_rotate and rot in (90, 180, 270) and img.width != pix.width:
        img = img.rotate(-rot, expand=True)

    if crop_box:
        img = img.crop(crop_box)
    return img


def pdf_page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    n   = doc.page_count
    doc.close()
    return n


# ── Image preprocessing for OCR [W3] ──────────────────────────────────────────
def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    Greyscale + autocontrast + light unsharp + threshold.
    Significantly improves Tesseract accuracy on scanned engineering drawings.
    """
    img = img.convert("L")                      # greyscale
    img = ImageOps.autocontrast(img, cutoff=2)  # stretch histogram
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
    # Light binarization — threshold at ~180 to keep faint dim-line text
    img = img.point(lambda p: 0 if p < 180 else 255, mode="L")
    return img


# ── AI disk cache [W1] ────────────────────────────────────────────────────
def _cache_path(image_bytes: bytes, prompt: str) -> str:
    h = hashlib.sha256()
    h.update(image_bytes)
    h.update(b"\x00")
    h.update(prompt.encode("utf-8"))
    h.update(b"\x00")
    h.update(AI_MODEL.encode("utf-8"))
    return os.path.join(CACHE_DIR, h.hexdigest() + ".txt")


def _cache_get(image_bytes: bytes, prompt: str) -> str | None:
    if not AI_CACHE_ENABLED:
        return None
    p = _cache_path(image_bytes, prompt)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def _cache_put(image_bytes: bytes, prompt: str, response: str):
    if not AI_CACHE_ENABLED:
        return
    p = _cache_path(image_bytes, prompt)
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(response)
    except Exception as e:
        log.warning(f"cache write failed: {e}")


# ── AI Vision wrapper [W1, W2, KEY_ROT] ──────────────────────────────────
def ask_ai(img: Image.Image, prompt: str, retries: int = AI_RETRIES,
               api_key: str | None = None, use_cache: bool = True) -> str:
    """
    Send a PIL image + prompt to AI Vision.

    Key-rotation strategy [KEY_ROT]:
      - On every attempt a fresh key is pulled from KeyManager.
      - On 429 / RESOURCE_EXHAUSTED the current key is marked exhausted
        and the NEXT key is used immediately — no wait, no interruption.
      - On 503 / 500 the same key is retried after a short back-off.
      - Raises RuntimeError only when ALL keys are exhausted.
    """
    from google.genai import types

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    image_bytes = buf.read()

    # ── Cache hit — no API call needed ───────────────────────────────────────
    if use_cache:
        cached = _cache_get(image_bytes, prompt)
        if cached is not None:
            log.debug("cache HIT")
            return cached

    mgr      = get_key_manager()
    last_err = None

    for attempt in range(retries):
        # Pick the next combination of key and model
        if api_key:
            current_key = api_key
            current_model = AI_MODEL
        else:
            current_key, current_model = mgr.get_key_and_model()
            
        if current_key is None:
            raise RuntimeError(
                "All AI API keys and models are exhausted for today. "
                "Counts reset at midnight UTC."
            )

        client = get_ai_client(current_key)
        try:
            part = types.Part.from_bytes(data=image_bytes, mime_type='image/png')
            r    = client.models.generate_content(
                model=current_model,
                contents=[part, prompt],
            )
            text = r.text or ""
            if not text.strip():
                last_err = RuntimeError("Empty response from AI")
                log.warning(f"empty response on attempt {attempt+1} — retrying")
                time.sleep(2)
                continue

            if use_cache:
                _cache_put(image_bytes, prompt, text)
            return text   #  success

        except Exception as e:
            last_err = e
            msg = str(e)

            # ── Rate-limit / quota → rotate key immediately ────────────────
            if any(code in msg for code in ("429", "RESOURCE_EXHAUSTED", "quota")):
                log.warning(
                    f"[KEY_ROT] Combo ...{current_key[-6:]} + {current_model} exhausted "
                    f"(attempt {attempt+1}) — switching to next combo instantly"
                )
                if not api_key:
                    mgr.mark_rate_limited(current_key, current_model)
                # No sleep — next iteration picks a fresh key right away
                continue

            # ── Server errors → short back-off, same key ───────────────────
            if any(code in msg for code in ("503", "500", "unavailable")):
                wait = AI_RETRY_WAIT_S * (attempt + 1)
                log.warning(
                    f"Server error on attempt {attempt+1}/{retries} "
                    f"— retrying in {wait}s"
                )
                time.sleep(wait)
                continue

            # ── Other transient error ──────────────────────────────────────
            if attempt < retries - 1:
                log.warning(f"transient error: {msg[:120]} — retrying in 5s")
                time.sleep(5)
            else:
                break

    raise RuntimeError(
        f"AI Vision failed after {retries} attempts across all keys. "
        f"Last error: {last_err}"
    )


def parse_json(raw: str) -> dict:
    """Tolerant JSON parser for AI outputs."""
    clean = re.sub(r'```(?:json)?', '', raw).strip().strip('`').strip()
    start = clean.find('{')
    end   = clean.rfind('}')
    if start >= 0 and end > start:
        return json.loads(clean[start:end+1])
    raise ValueError("No JSON object found in response")


# ── Token normalization [W5] ──────────────────────────────────────────────────
_TOKEN_NORM_RE = re.compile(r'[\s\-_./]+')


def normalize_mark(token: str) -> str:
    """
    Canonicalize a label token for robust matching.
    Handles 'D1' / 'D 1' / 'D-1' / 'D.1' / 'D/1' / 'd1' → 'D1'.
    """
    return _TOKEN_NORM_RE.sub('', token).upper()


# ── Text extraction: fitz with OCR fallback ───────────────────────────────────
def is_pdf_text_based(pdf_path: str, sample_pages: int = 5) -> bool:
    """Check if a PDF has real text (fitz can read) vs. fully scanned (raster)."""
    doc = fitz.open(pdf_path)
    try:
        sample_n = min(sample_pages, doc.page_count)
        text_pages = 0
        for i in range(sample_n):
            if len(doc[i].get_text("words")) > 20:
                text_pages += 1
        return text_pages >= max(1, sample_n // 2)
    finally:
        doc.close()


def extract_words_fitz(pdf_path: str, page_index: int) -> list[tuple]:
    """Returns fitz word tuples: [(x0, y0, x1, y1, word, block, line, word_no), ...]."""
    doc = fitz.open(pdf_path)
    try:
        return doc[page_index].get_text("words")
    finally:
        doc.close()


def extract_text_ocr(img: Image.Image, lang: str = "eng",
                     preprocess: bool = True) -> list[dict]:
    """OCR fallback. Returns [{"text", "x", "y", "conf"}]."""
    if preprocess:
        img = preprocess_for_ocr(img)
    # ── Try Tesseract ─────────────────────────────────────────────────────────
    try:
        import pytesseract
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
        out  = []
        for i in range(len(data['text'])):
            txt = data['text'][i].strip()
            if not txt:
                continue
            try:
                conf = float(data['conf'][i])
            except (ValueError, TypeError):
                conf = 0
            if conf < 30:
                continue
            out.append({
                "text": txt,
                "x":    data['left'][i] + data['width'][i] // 2,
                "y":    data['top'][i]  + data['height'][i] // 2,
                "conf": conf,
            })
        return out
    except Exception as e:
        log.debug(f"tesseract unavailable: {e}")

    # ── Fall back to EasyOCR ──────────────────────────────────────────────────
    try:
        import easyocr, numpy as np
        reader  = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(np.array(img))
        out     = []
        for bbox, txt, conf in results:
            if conf < 0.3 or not txt.strip():
                continue
            cx = int((bbox[0][0] + bbox[2][0]) / 2)
            cy = int((bbox[0][1] + bbox[2][1]) / 2)
            out.append({
                "text": txt.strip(),
                "x":    cx,
                "y":    cy,
                "conf": round(conf * 100, 1),
            })
        return out
    except Exception as e:
        log.error(f"OCR fallback failed: {e}")
        return []


def count_token_in_page(pdf_path: str, page_index: int, tokens: list[str],
                        dpi_for_ocr: int = 300) -> dict[str, int]:
    """
    Count exact-match occurrences of given tokens on a page, with normalization [W5].

    Normalization is applied to BOTH the search tokens and the page tokens, so
    'D-1' on the page matches 'D1' in the search list, etc.

    Combines vector text, OCR text, and AI Vision counting fallback to ensure
    robust counts even on scanned floor plans with small circular/hexagonal labels.

    Returns dict keyed by NORMALIZED token (uppercase, no whitespace/hyphens).
    Callers should look up their tokens via normalize_mark() to match.
    """
    norm_tokens = {normalize_mark(t): 0 for t in tokens}
    if not tokens:
        return norm_tokens

    # 1. Search vector words
    words = extract_words_fitz(pdf_path, page_index)
    if words:
        for w in words:
            n = normalize_mark(w[4])
            if n in norm_tokens:
                norm_tokens[n] += 1

    # 2. Run OCR
    img = render_page(pdf_path, page_index, dpi=dpi_for_ocr)
    ocr_rs = extract_text_ocr(img)
    ocr_counts = {normalize_mark(t): 0 for t in tokens}
    for r in ocr_rs:
        n = normalize_mark(r['text'])
        if n in ocr_counts:
            ocr_counts[n] += 1

    # Combine Vector + OCR by taking the maximum for each token
    for n in norm_tokens:
        norm_tokens[n] = max(norm_tokens[n], ocr_counts.get(n, 0))

    # 3. AI Vision Fallback: if some tokens are still 0, run AI vision to count
    zero_tokens = [t for t in tokens if norm_tokens[normalize_mark(t)] == 0]
    if zero_tokens:
        log.info(f"page {page_index+1}: {len(zero_tokens)} tokens have 0 counts — running AI vision count fallback")
        prompt = f"""You are looking at an architectural floor plan drawing for a UAE building.
Count the exact number of occurrences of each of the following door/window tags/labels on this drawing sheet.
Look for them in circular or hexagonal symbols near door openings or windows.
Tags to search for: {', '.join(tokens)}

Return ONLY a JSON dictionary where the keys are the exact tags and the values are their integer counts on this page.
Do not explain, do not add extra text, return ONLY the JSON:
{{
  {', '.join(f'"{t}": <count>' for t in tokens)}
}}
"""
        try:
            raw = ask_ai(img, prompt)
            parsed = parse_json(raw)
            for t in tokens:
                n = normalize_mark(t)
                ai_count = int(parsed.get(t) or parsed.get(n) or 0)
                norm_tokens[n] = max(norm_tokens[n], ai_count)
        except Exception as e:
            log.warning(f"AI count fallback failed on page {page_index+1}: {e}")

    return norm_tokens
