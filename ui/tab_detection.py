"""
تبويب كشف العناصر بـ OpenCV — assigned pages only
"""
import streamlit as st
import pandas as pd

from pdf_engine.element_detector import (
    detect_columns, detect_walls, detect_rooms,
    draw_detections, calculate_detection_summary,
)
from pdf_engine.pdf_loader import page_to_pil


def render_detection_tab() -> dict:
    st.header("️ Detect Elements | كشف العناصر")

    classified = st.session_state.get("all_classified_pages", [])
    all_images = st.session_state.get("all_pages_images", {})
    ppm        = st.session_state.get("pixels_per_meter", 0.0)

    if not classified:
        st.warning(" Upload and classify PDFs first in the PDF Upload tab.")
        return {}

    # Only assigned pages — same rule as every other tab
    assigned = [p for p in classified if p["detected_type"] != "unknown"]

    if not assigned:
        st.warning(" No pages assigned yet. Go to PDF Upload tab and assign drawing types.")
        return {}

    if ppm <= 0:
        st.warning(" Set the drawing scale in the PDF Upload tab first.")
        return {}

    # ── Page selector ─────────────────────────────────────────────────────────
    page_labels = {
        f"{p['pdf_name'].title()} · Page {p['page_number']} — "
        f"{p['detected_type'].replace('_', ' ').title()}": p
        for p in assigned
    }

    selected_label = st.selectbox(
        "Select page to detect | اختر صفحة للكشف",
        options=list(page_labels.keys()),
        key="det_page_select",
    )
    selected = page_labels[selected_label]

    pages_src = all_images.get(selected["pdf_name"], [])
    if selected["page_index"] >= len(pages_src):
        st.error("Page image not found.")
        return {}

    page_array = pages_src[selected["page_index"]]

    st.caption(
        f" Scale: **{ppm:.1f} px/m** | "
        f"Type: **{selected['detected_type'].replace('_', ' ').title()}** | "
        f"{selected['pdf_name'].title()} · Page {selected['page_number']}"
    )

    # ── Settings ──────────────────────────────────────────────────────────────
    with st.expander(" Detection Settings | إعدادات الكشف"):
        col_min = st.slider("Min column size (m)", 0.10, 0.50, 0.20, 0.05, key="det_col_min")
        col_max = st.slider("Max column size (m)", 0.50, 2.00, 1.00, 0.10, key="det_col_max")

    # ── Detect button ─────────────────────────────────────────────────────────
    det_key = f"det_{selected['pdf_name']}_{selected['page_index']}"

    if st.button(" Detect Elements | كشف العناصر", type="primary", key="btn_detect"):
        with st.spinner("Detecting... | جاري الكشف..."):
            columns = detect_columns(page_array, ppm, col_min, col_max)
            walls   = detect_walls(page_array, ppm)
            rooms   = detect_rooms(page_array, ppm)
            summary = calculate_detection_summary(columns, walls, rooms)

            st.session_state[f"{det_key}_columns"] = columns
            st.session_state[f"{det_key}_walls"]   = walls
            st.session_state[f"{det_key}_rooms"]   = rooms
            st.session_state[f"{det_key}_summary"] = summary
            # Also keep flat refs for downstream tabs
            st.session_state["detected_columns"]   = columns
            st.session_state["detected_walls"]     = walls
            st.session_state["detected_rooms"]     = rooms
            st.session_state["detection_summary"]  = summary

    columns = st.session_state.get(f"{det_key}_columns", [])
    walls   = st.session_state.get(f"{det_key}_walls",   [])
    rooms   = st.session_state.get(f"{det_key}_rooms",   [])
    summary = st.session_state.get(f"{det_key}_summary", {})

    if not summary:
        st.image(page_to_pil(page_array), use_container_width=True,
                 caption="Preview — click Detect to analyze")
        st.info("Click the button above to detect structural elements.")
        return {}

    # ── Metrics ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Columns",         summary.get("column_count", 0))
    c2.metric("Total Walls (m)", summary.get("total_wall_m", 0))
    c3.metric("Rooms",           summary.get("room_count", 0))
    c4.metric("Total Area (m²)", summary.get("total_area_m2", 0))

    # ── Annotated image ───────────────────────────────────────────────────────
    annotated = draw_detections(page_array, columns, walls, rooms)
    st.image(
        page_to_pil(annotated),
        caption=" Columns |  Walls |  Rooms",
        use_container_width=True,
    )

    # ── Column Schedule ───────────────────────────────────────────────────────
    st.markdown("###  Column Schedule | جدول الأعمدة")
    if summary.get("column_schedule"):
        st.dataframe(
            pd.DataFrame([
                {"Size (m)": size, "Count": count}
                for size, count in summary["column_schedule"].items()
            ]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No columns detected.")

    # ── Rooms ─────────────────────────────────────────────────────────────────
    st.markdown("###  Detected Rooms | الغرف المكتشفة")
    if rooms:
        st.dataframe(
            pd.DataFrame([{
                "Area (m²)":     r["area_m2"],
                "Width (m)":     r["width_m"],
                "Length (m)":    r["height_m"],
                "Perimeter (m)": r["perim_m"],
            } for r in rooms[:20]]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No rooms detected.")

    # ── Send to Engine ────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button(" Send to QTO Engine | إرسال للمحرك", type="primary", key="btn_det_send"):
        st.session_state["auto_populated"] = True
        st.success(" Detection data saved. Use Review & Confirm tab to verify before BOQ.")

    return summary
