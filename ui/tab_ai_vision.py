"""
AI Vision مع تحليل موجّه لكل صفحة حسب نوعها — AI
"""
import streamlit as st
import json
import re
import io
import os
import numpy as np
from PIL import Image

from pdf_engine.smart_classifier import PAGE_ITEMS_MAP
from pdf_engine.drawing_prompts  import build_prompt

MODEL = "gemini-3.1-flash-lite"


def _page_to_png_bytes(page_array: np.ndarray, max_px: int = 2000) -> bytes:
    rgb = page_array[:, :, ::-1].copy()
    pil = Image.fromarray(rgb)
    w, h = pil.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        pil   = pil.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    pil.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def analyze_page_targeted(
    page_array:    np.ndarray,
    page_type:     str,
    ai_focus:      str,      # kept for signature compat, overridden by build_prompt
    extract_items: list,
    ppm:           float = 0.0,
) -> dict:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("AI_API_KEY")
    if not api_key:
        return {"_success": False, "_error": "GOOGLE_API_KEY not set", "page_type": page_type}

    from google import genai
    from google.genai import types

    client    = genai.Client(api_key=api_key)
    img_bytes = _page_to_png_bytes(page_array)

    # Use detailed drawing-specific prompt (concept from simple app)
    scale_note = f"\nDrawing scale: {ppm:.1f} pixels/meter.\n" if ppm > 0 else ""
    prompt = scale_note + build_prompt(page_type)

    # dummy replacement to keep old structure valid (prompt is now self-contained)
    _ = ai_focus  # no longer used directly — build_prompt handles it

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                prompt,
            ],
        )
        raw  = response.text.strip()
        raw  = re.sub(r"```json\s*|```", "", raw).strip()
        data = json.loads(raw)
        data["_success"]   = True
        data["page_type"]  = page_type
        return data
    except Exception as e:
        return {"_success": False, "_error": str(e), "page_type": page_type}


def render_ai_vision_tab() -> dict:
    st.header(" AI Vision — Smart Targeted Analysis")
    st.caption("Each page is analyzed ONLY for its specific QTO items.")

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("AI_API_KEY")
    if not api_key:
        st.error(
            "GOOGLE_API_KEY not found. Get a free key at https://aistudio.google.com/apikey then run:\n\n"
            "`setx GOOGLE_API_KEY AIza...`\n\nand restart the app."
        )
        return {}

    classified = st.session_state.get("all_classified_pages", [])
    ppm        = st.session_state.get("pixels_per_meter", 0.0)
    all_images = st.session_state.get("all_pages_images", {})

    if not classified:
        st.warning(" Upload and classify PDFs first in the PDF Upload tab.")
        return {}

    ready_pages = [p for p in classified if p["detected_type"] != "unknown"]
    st.info(f" Ready to analyze: **{len(ready_pages)} pages** | Each page targets only its relevant QTO items")

    with st.expander("️ Preview: What AI will extract per page"):
        for p in ready_pages:
            st.markdown(f"**Page {p['page_number']} ({p['pdf_name']})** → `{p['detected_type']}`")
            items_preview = p["extract_items"][:5]
            suffix = "..." if len(p["extract_items"]) > 5 else ""
            st.caption(f"Items: {', '.join(items_preview)}{suffix}")

    if st.button(
        f" Analyze All {len(ready_pages)} Pages | تحليل كل الصفحات",
        type="primary",
        key="btn_analyze_all",
    ):
        results  = {}
        progress = st.progress(0)
        status   = st.empty()

        for i, page_info in enumerate(ready_pages):
            pdf_src   = page_info["pdf_name"]
            page_idx  = page_info["page_index"]
            page_type = page_info["detected_type"]
            ai_focus  = page_info["ai_focus"]
            items     = page_info["extract_items"]

            status.info(
                f" Analyzing page {page_info['page_number']} ({pdf_src})"
                f" — {page_type.replace('_', ' ').title()}"
            )

            pages_src = all_images.get(pdf_src, [])
            if page_idx < len(pages_src):
                result = analyze_page_targeted(
                    pages_src[page_idx], page_type, ai_focus, items, ppm
                )
                key = f"{pdf_src}_p{page_info['page_number']}_{page_type}"
                results[key] = result

            progress.progress((i + 1) / len(ready_pages))

        st.session_state["ai_vision_results"] = results
        status.success(" Analysis complete!")
        progress.empty()

    results = st.session_state.get("ai_vision_results", {})
    if not results:
        return {}

    success = sum(1 for r in results.values() if r.get("_success"))
    st.success(f" {success}/{len(results)} pages analyzed successfully")

    for key, data in results.items():
        page_label = key.replace("_", " ").title()
        with st.expander(f" {page_label}"):
            if not data.get("_success"):
                st.error(f"❌ {data.get('_error', 'Failed')}")
                continue
            conf_val  = str(data.get("confidence", "low"))
            conf_icon = {"high": "", "medium": "", "low": ""}.get(
                conf_val.lower(), "⚪"
            )
            st.markdown(f"Confidence: {conf_icon} {conf_val.upper()}")
            extracted = data.get("extracted", {})
            if extracted:
                st.json(extracted)
            if data.get("notes"):
                st.caption(f" {data['notes']}")

    if st.button(" Send to Review & Confirm Tab", type="primary", key="btn_send_review"):
        st.session_state["ai_analysis_done"] = True
        st.success(" Go to Review & Confirm tab!")

    return results
