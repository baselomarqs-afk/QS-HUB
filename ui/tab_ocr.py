"""
تبويب OCR — يعمل على الصفحات المصنفة فقط ويجمع النتائج معاً
Primary: fitz direct text extraction (fast, accurate for CAD PDFs)
Fallback: EasyOCR for scanned/rasterised drawings
"""
import streamlit as st
import pandas as pd

from pdf_engine.ocr_engine      import extract_dimensions_from_plain_text
from pdf_engine.scale_detector  import calculate_ppm
from pdf_engine.pdf_loader      import page_to_pil
from engine.dimension_filter    import filter_ocr_by_drawing_inputs


def render_ocr_tab() -> dict:
    st.header(" OCR — All Assigned Pages | استخراج الأبعاد من الصفحات المصنفة")

    classified  = st.session_state.get("all_classified_pages", [])
    all_images  = st.session_state.get("all_pages_images", {})
    ppm         = st.session_state.get("pixels_per_meter", 0.0)

    # Fallback: if multi-PDF not used, try legacy single-PDF mode
    if not classified:
        pages = st.session_state.get("pdf_pages", [])
        if not pages:
            st.warning("Upload and classify PDFs first in the PDF Upload tab.")
            return {}
        classified = [
            {"page_index": i, "page_number": i + 1, "pdf_name": "pdf",
             "detected_type": "unknown", "confidence": "low"}
            for i in range(len(pages))
        ]
        all_images = {"pdf": pages}

    if ppm <= 0:
        st.warning("Set the drawing scale in the PDF Upload tab first.")
        return {}

    # Only assigned pages
    assigned = [p for p in classified if p["detected_type"] != "unknown"]

    if not assigned:
        st.warning("No pages have been assigned a drawing type yet. Go to PDF Upload tab and assign types, then Confirm.")
        return {}

    st.info(
        f" **{len(assigned)} assigned pages** will be processed | "
        f"Scale: **{ppm:.1f} px/m**"
    )

    # Page text lookup (fitz-extracted, stored during PDF load)
    page_texts: dict[str, list[str]] = {
        "structural":    st.session_state.get("str_page_texts", []),
        "architectural": st.session_state.get("arch_page_texts", []),
        "pdf":           [],
    }

    # Preview which pages will be processed
    with st.expander("️ Pages to process", expanded=False):
        for p in assigned:
            conf_icon = {"high": "", "medium": "", "low": "", "manual": ""}.get(p["confidence"], "⚪")
            st.caption(
                f"{conf_icon} **{p['pdf_name'].title()} · Page {p['page_number']}** "
                f"→ {p['detected_type'].replace('_', ' ').title()}"
            )

    # ── Run OCR on all assigned pages ──────────────────────────────────────────
    if st.button(
        f" Run OCR on {len(assigned)} Pages | تشغيل OCR على كل الصفحات",
        type="primary",
        key="btn_run_ocr_all",
    ):
        all_dims    = []
        page_results = {}
        progress    = st.progress(0)
        status      = st.empty()

        for i, pinfo in enumerate(assigned):
            pdf_src  = pinfo["pdf_name"]
            page_idx = pinfo["page_index"]
            dtype    = pinfo["detected_type"]
            label    = f"{pdf_src.title()} · Page {pinfo['page_number']} ({dtype.replace('_',' ').title()})"

            status.info(f" OCR: {label}")

            pages_src = all_images.get(pdf_src, [])
            if page_idx >= len(pages_src):
                progress.progress((i + 1) / len(assigned))
                continue

            page_arr = pages_src[page_idx]

            try:
                # ── Primary: fitz direct text (instant, no model needed) ──
                texts_for_pdf = page_texts.get(pdf_src, [])
                fitz_text     = texts_for_pdf[page_idx] if page_idx < len(texts_for_pdf) else ""

                if fitz_text.strip():
                    dims         = extract_dimensions_from_plain_text(fitz_text)
                    # Keep only numbers that formula inputs for this drawing type need
                    dims         = filter_ocr_by_drawing_inputs(dims, dtype)
                    text_results = []
                    method       = "PDF text"
                else:
                    # No embedded text — scanned page, skip silently
                    dims         = []
                    text_results = []
                    method       = "no text"

                scale_found = None

                for d in dims:
                    d["source_page"]  = pinfo["page_number"]
                    d["source_pdf"]   = pdf_src
                    d["drawing_type"] = dtype

                all_dims.extend(dims)

                key = f"{pdf_src}_p{pinfo['page_number']}_{dtype}"
                page_results[key] = {
                    "text_results": text_results,
                    "dimensions":   dims,
                    "scale_found":  scale_found,
                    "label":        label,
                    "page_type":    dtype,
                    "method":       method,
                }

                if scale_found:
                    new_ppm = calculate_ppm(scale_found)
                    if new_ppm:
                        st.session_state["pixels_per_meter"] = new_ppm
                        ppm = new_ppm

            except Exception as e:
                st.warning(f"OCR failed on {label}: {e}")

            progress.progress((i + 1) / len(assigned))

        st.session_state["ocr_dimensions"]   = all_dims
        st.session_state["ocr_page_results"] = page_results
        st.session_state["ocr_text_results"] = []

        status.success(
            f" OCR complete — {len(all_dims)} dimensions found across {len(assigned)} pages"
        )
        progress.empty()

    # ── Show combined results ──────────────────────────────────────────────────
    all_dims     = st.session_state.get("ocr_dimensions", [])
    page_results = st.session_state.get("ocr_page_results", {})

    if not all_dims and not page_results:
        st.info("Click the button above to start OCR.")
        return {}

    st.success(f"**{len(all_dims)} dimensions** extracted from **{len(page_results)} pages**")

    # ── Per-page breakdown ──
    st.markdown("###  Results by Page | النتائج حسب الصفحة")

    for key, pr in page_results.items():
        dims_here = pr["dimensions"]
        method    = pr.get("method", "")
        with st.expander(
            f" {pr['label']} — {len(dims_here)} dimensions [{method}]",
            expanded=len(dims_here) > 0,
        ):
            if pr.get("scale_found"):
                st.caption(f" Scale detected in drawing: `{pr['scale_found']}`")

            if dims_here:
                df = pd.DataFrame([{
                    "Value (m)":  d["value_meters"],
                    "Original":   d["original_text"],
                    "Confidence": f"{d['confidence']:.0%}",
                } for d in dims_here])
                st.dataframe(df, use_container_width=True, hide_index=True, height=200)
            else:
                st.caption("No dimensions found on this page.")

    # ── Combined table ──
    st.markdown("---")
    st.markdown("###  All Dimensions Combined | كل الأبعاد مجتمعة")

    if all_dims:
        combined_df = pd.DataFrame([{
            "Value (m)":    d["value_meters"],
            "Original":     d["original_text"],
            "Drawing Type": d.get("drawing_type", "").replace("_", " ").title(),
            "Page":         d.get("source_page", ""),
            "PDF":          d.get("source_pdf", "").title(),
            "Confidence":   f"{d['confidence']:.0%}",
        } for d in all_dims]).sort_values("Value (m)", ascending=False)

        st.dataframe(combined_df, use_container_width=True, height=400, hide_index=True)

        # ── Manual keep/remove ──
        st.markdown("---")
        st.markdown("### ✏️ Keep / Remove | احتفظ أو أزل")
        st.caption("Uncheck 'Keep' to exclude a dimension before passing to the engine.")

        edit_df = st.data_editor(
            pd.DataFrame([{
                "Value (m)": d["value_meters"],
                "Type":      d.get("drawing_type", "").replace("_", " ").title(),
                "Keep":      True,
            } for d in all_dims]),
            use_container_width=True,
            key="dim_editor_all",
            column_config={
                "Value (m)": st.column_config.NumberColumn(format="%.3f"),
                "Keep":      st.column_config.CheckboxColumn(),
            },
        )

        kept = [
            all_dims[i]
            for i, row in edit_df.iterrows()
            if row.get("Keep", True)
        ]

        values = sorted([d["value_meters"] for d in kept], reverse=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Kept dimensions", len(kept))
        c2.metric("Largest (m)",  f"{values[0]:.2f}"  if values else 0)
        c3.metric("Smallest (m)", f"{values[-1]:.2f}" if values else 0)

        return {
            "dimensions":   kept,
            "all_values_m": values,
            "ppm":          ppm,
        }

    return {}
