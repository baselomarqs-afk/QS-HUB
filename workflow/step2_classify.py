"""
STEP 2 — Classify Pages
AI reads each page title/text and assigns drawing type
User can correct any misclassification
"""
import pandas as pd
import os, io, re, json
from pdf_engine.smart_classifier import classify_all_pages, PAGE_ITEMS_MAP
from pdf_engine.pdf_loader import page_to_pil
from workflow.workflow_state import mark_step_done

# Candidate types per PDF kind — used by the AI-vision refiner
_STRUCT_TYPES = ["foundations", "tie_beam", "column_layout", "upper_columns", "neck_columns",
                 "columns_1f", "columns_2f", "columns_roof",
                 "slab_1st", "slab_2nd", "roof_slab"]
_ARCH_TYPES   = ["ground_floor_plan", "first_floor_plan", "second_floor_plan",
                 "roof_floor_plan", "elevations", "setting_out", "schedules"]


def _ai_classify(page_arr, pdf_type: str):
    """Classify ONE page by vision when keyword matching is unsure. Returns a
    PAGE_ITEMS_MAP key or None."""
    from utils.key_manager import get_key_manager
    mgr = get_key_manager()
    api_key, current_model = mgr.get_key_and_model()
    if not api_key or api_key == "NO_API_KEY_FOUND":
        return None
    choices = _STRUCT_TYPES if pdf_type == "structural" else _ARCH_TYPES
    try:
        from google import genai
        from google.genai import types
        import time
        import io as _io

        pil_img = page_to_pil(page_arr)
        buf = _io.BytesIO()
        pil_img.save(buf, format="PNG")
        img = buf.getvalue()
        prompt = (
            f"This is a construction drawing. Classify it as one of: {choices}. "
            "Reply ONLY with valid JSON: {\"type\": \"<chosen_type>\"}"
        )

        for attempt in range(5):
            api_key, current_model = mgr.get_key_and_model()
            if not api_key or api_key == "NO_API_KEY_FOUND":
                return None

            try:
                client = genai.Client(api_key=api_key, http_options={'timeout': 60})
                resp = client.models.generate_content(
                    model=current_model,
                    contents=[types.Part.from_bytes(data=img, mime_type="image/png"), prompt])
                raw = re.sub(r"```json|```", "", resp.text).strip()
                result = json.loads(raw).get("type")
                return result if result in PAGE_ITEMS_MAP else None
            except Exception as e:
                last_err = str(e)
                if any(code in last_err for code in ("429", "RESOURCE_EXHAUSTED", "quota")):
                    mgr.mark_rate_limited(api_key, current_model)
                    continue
                time.sleep(2)

        return None
    except Exception:
        return None


from utils.i18n import t

def render_step2() -> bool:
    import streamlit as st
    st.markdown(t("classify_title"))
    st.caption(t("classify_caption"))

    str_pages  = st.session_state.get("str_pages", [])
    arch_pages = st.session_state.get("arch_pages", [])
    str_texts  = st.session_state.get("str_texts", [])
    arch_texts = st.session_state.get("arch_texts", [])

    # Auto-classify if not done yet
    if "classified_pages" not in st.session_state:
        with st.spinner(t("classify_running")):
            classified = []
            for i, txt in enumerate(str_texts):
                classified.append({
                    "pdf":        "structural",
                    "page_index": i,
                    "page_num":   i + 1,
                    "text_preview": txt[:100].replace("\n", " "),
                    **_classify_single(txt, "structural"),
                })
            for i, txt in enumerate(arch_texts):
                classified.append({
                    "pdf":        "architectural",
                    "page_index": i,
                    "page_num":   i + 1,
                    "text_preview": txt[:100].replace("\n", " "),
                    **_classify_single(txt, "architectural"),
                })

        # Verify EVERY page with AI Vision (more reliable than keywords on
        # unseen drawings). Vision wins when it returns a valid type.
        prog = st.progress(0.0, text="AI-verifying every page by image…")
        for n, p in enumerate(classified):
            src = str_pages if p["pdf"] == "structural" else arch_pages
            if p["page_index"] < len(src):
                g = _ai_classify(src[p["page_index"]], p["pdf"])
                if g:
                    p["detected_type"] = g
                    p["confidence"]    = "high(ai)"
                    p["items"] = PAGE_ITEMS_MAP.get(g, {}).get("extract_items", [])
            prog.progress((n + 1) / len(classified))
        prog.empty()

        st.session_state["classified_pages"] = classified

    classified = st.session_state["classified_pages"]

    # Show classification results as editable table
    st.markdown("### Auto-Classification Results | نتائج التصنيف التلقائي")

    drawing_types = ["unknown"] + list(PAGE_ITEMS_MAP.keys())

    for page in classified:
        col_img, col_info, col_edit = st.columns([2, 2, 2])

        pages_src = (
            st.session_state.get("str_pages", []) if page["pdf"] == "structural"
            else st.session_state.get("arch_pages", [])
        )

        with col_img:
            if page["page_index"] < len(pages_src):
                st.image(
                    page_to_pil(pages_src[page["page_index"]]),
                    caption=f"{page['pdf']} P{page['page_num']}",
                    use_container_width=True
                )

        with col_info:
            _conf = str(page.get("confidence", "low"))
            conf_icon = "" if _conf.startswith("high") else {"medium": "", "low": ""}.get(_conf, "⚪")
            ai_tag = " (AI vision)" if "ai" in _conf else ""
            st.markdown(f"**{conf_icon} Auto-detected{ai_tag}:**")
            st.markdown(f"`{page.get('detected_type','unknown')}`")
            st.caption(page["text_preview"])

        with col_edit:
            current_idx = drawing_types.index(page.get("detected_type","unknown")) if page.get("detected_type","unknown") in drawing_types else 0
            new_type = st.selectbox(
                "Drawing Type",
                options=drawing_types,
                index=current_idx,
                key=f"cls_{page['pdf']}_{page['page_index']}",
                format_func=lambda x: x.replace("_", " ").title() if x != "unknown" else " Unknown — select type"
            )
            page["detected_type"] = new_type
            if new_type != "unknown":
                page["items"] = PAGE_ITEMS_MAP.get(new_type, {}).get("extract_items", [])

        st.divider()

    # Update session state
    st.session_state["classified_pages"] = classified

    ready = [p for p in classified if p["detected_type"] != "unknown"]
    unknown = [p for p in classified if p["detected_type"] == "unknown"]

    if unknown:
        st.warning(f" {len(unknown)} pages still unclassified — please assign types above")

    st.info(f" {len(ready)} pages ready for extraction")

    if ready and st.button(t("classify_next_btn"), type="primary", use_container_width=True):
        mark_step_done("classify")
        return True

    return False



def _classify_single(text: str, pdf_type: str) -> dict:
    from pdf_engine.smart_classifier import PAGE_ITEMS_MAP
    text_lower = text.lower()
    scores = {}
    for ptype, config in PAGE_ITEMS_MAP.items():
        score = sum(1 for kw in config.get("drawing_keywords", []) if kw.lower() in text_lower)
        scores[ptype] = score
    best  = max(scores, key=scores.get)
    score = scores[best]
    return {
        "detected_type": best if score > 0 else "unknown",
        "confidence": "high" if score >= 2 else "medium" if score == 1 else "low",
        "items": PAGE_ITEMS_MAP.get(best, {}).get("extract_items", []) if score > 0 else [],
    }
