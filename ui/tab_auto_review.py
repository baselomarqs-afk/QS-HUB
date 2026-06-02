"""
تبويب مراجعة وتأكيد البيانات المستخرجة تلقائياً
"""
import streamlit as st
import pandas as pd
from engine.auto_populator import build_auto_populated_state
from engine.item_calculator import validate_takeoff_inputs


_FLOOR_LABELS = {
    "gf":   "Ground Floor | الأرضي",
    "f1":   "1st Floor | الأول",
    "f2":   "2nd Floor | الثاني",
    "roof": "Roof | السطح",
}

_SOURCE_COLORS = {
    "ai_vision":    "",
    "ocr_estimated":"",
    "opencv":       "",
}


def _push_to_finishes_state(confirmed_data: dict):
    """Pushes confirmed floor data into the session_state keys that tab_finishes reads."""
    for fk, fdata in confirmed_data.items():
        if fk == "substructure":
            continue
        for field, ss_key in [
            ("wet_area",         f"fin_{fk}_wet_area"),
            ("wet_perimeter",    f"fin_{fk}_wet_perimeter"),
            ("dry_perimeter",    f"fin_{fk}_dry_perimeter"),
            ("int_walls_length", f"fin_{fk}_int_walls_length"),
            ("balcony_area",     f"fin_{fk}_balcony_area"),
        ]:
            val = fdata.get(field)
            if val is not None:
                st.session_state[ss_key] = float(val)


def _push_to_substructure_state(sub_data: dict):
    """Pushes confirmed sub-structure data into tab_substructure session_state keys."""
    if sub_data.get("foundations"):
        st.session_state["sub_foundations"] = pd.DataFrame(sub_data["foundations"])
    if sub_data.get("neck_columns"):
        st.session_state["sub_neck_cols"]   = pd.DataFrame(sub_data["neck_columns"])
    st.session_state["sub_tb_width"]  = float(sub_data.get("tb_width",  0.30))
    st.session_state["sub_tb_depth"]  = float(sub_data.get("tb_depth",  0.50))
    st.session_state["sub_tb_length"] = float(sub_data.get("tb_length", 0.0))


def render_auto_review_tab(project: dict) -> dict:
    st.header(" Review & Confirm Auto-Extracted Data | مراجعة البيانات")

    ai_results = st.session_state.get("ai_vision_results", {})
    cv_summary = st.session_state.get("detection_summary", {})
    ocr_dims   = st.session_state.get("ocr_dimensions", [])
    num_floors = project.get("num_floors", 2)

    if not ai_results and not cv_summary:
        st.warning("No auto-extracted data yet. Run AI Vision (tab ) first.")
        return {}

    auto_state = build_auto_populated_state(ai_results, cv_summary, ocr_dims, num_floors)

    # ── Self-Validation Alerts ──
    validation_inputs = {
        "gf_area": auto_state.get("auto_gf", {}).get("floor_area", 0.0),
        "plot_area": project.get("plot_area", 1000.0),
        "tb_total_length": auto_state.get("auto_substructure", {}).get("tb_length", 0.0),
        "external_perimeter": auto_state.get("auto_gf", {}).get("ext_perimeter", 0.0),
        "foundations_schedule": auto_state.get("auto_substructure", {}).get("foundations", []),
        "doors_schedule": auto_state.get("auto_gf", {}).get("doors", []),
        "room_count": auto_state.get("auto_gf", {}).get("room_count", 0)
    }
    
    validation_warnings = validate_takeoff_inputs(validation_inputs)
    if validation_warnings:
        st.markdown("#### ⚠️ تنبيهات التدقيق الهندسي الذاتي (Self-Validation Alerts)")
        for warn in validation_warnings:
            st.warning(warn)

    n_ai  = len(ai_results)
    n_ocr = len(ocr_dims)
    st.success(f"Data from {n_ai} AI analysis result(s) + {n_ocr} OCR dimension(s)")
    st.markdown("**Review each floor, adjust if needed, then confirm.**")

    floor_keys    = ["gf", "f1", "f2"][:num_floors]
    confirmed_data = {}

    for fk in floor_keys:
        fdata = auto_state.get(f"auto_{fk}", {})
        label = _FLOOR_LABELS.get(fk, fk)

        with st.expander(f" {label}", expanded=(fk == "gf")):
            # Source legend
            sources = fdata.get("source", {})
            if sources:
                parts = [
                    f"{_SOURCE_COLORS.get(v,'⚪')} {k}: **{v}**"
                    for k, v in sources.items()
                ]
                st.caption("Sources — " + " | ".join(parts))

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Areas | المساحات**")
                fdata["floor_area"]   = st.number_input(
                    "Floor Area (m²)",   min_value=0.0, step=1.0,
                    value=float(fdata.get("floor_area") or 0),   key=f"rev_area_{fk}")
                fdata["wet_area"]     = st.number_input(
                    "Wet Area (m²)",     min_value=0.0, step=0.5,
                    value=float(fdata.get("wet_area") or 0),     key=f"rev_wet_{fk}")
                fdata["dry_area"]     = st.number_input(
                    "Dry Area (m²)",     min_value=0.0, step=0.5,
                    value=float(fdata.get("dry_area") or 0),     key=f"rev_dry_{fk}")
                fdata["balcony_area"] = st.number_input(
                    "Balcony Area (m²)", min_value=0.0, step=0.5,
                    value=float(fdata.get("balcony_area") or 0), key=f"rev_bal_{fk}")

            with col2:
                st.markdown("**Perimeters | المحيطات**")
                fdata["ext_perimeter"]    = st.number_input(
                    "Ext. Perimeter (m)",  min_value=0.0, step=0.5,
                    value=float(fdata.get("ext_perimeter") or 0),    key=f"rev_extp_{fk}")
                fdata["wet_perimeter"]    = st.number_input(
                    "Wet Perimeter (m)",   min_value=0.0, step=0.5,
                    value=float(fdata.get("wet_perimeter") or 0),    key=f"rev_wetp_{fk}")
                fdata["dry_perimeter"]    = st.number_input(
                    "Dry Perimeter (m)",   min_value=0.0, step=0.5,
                    value=float(fdata.get("dry_perimeter") or 0),    key=f"rev_dryp_{fk}")
                fdata["int_walls_length"] = st.number_input(
                    "Int. Walls (m)",      min_value=0.0, step=0.5,
                    value=float(fdata.get("int_walls_length") or 0), key=f"rev_intp_{fk}")

            # Columns editor
            cols = fdata.get("columns", [])
            if cols:
                st.markdown("**Columns | الأعمدة**")
                cols_df = pd.DataFrame(cols)
                edited  = st.data_editor(
                    cols_df, key=f"cols_edit_{fk}", use_container_width=True, num_rows="dynamic"
                )
                fdata["columns"] = edited.to_dict("records") if edited is not None else cols

            # Display interactive takeoff canvas for visual shading/verification
            all_pages_images = st.session_state.get("all_pages_images", {})
            all_classified = st.session_state.get("all_classified_pages", [])
            
            type_map = {
                "gf": "ground_floor_plan",
                "f1": "first_floor_plan",
                "f2": "second_floor_plan"
            }
            target_type = type_map.get(fk)
            
            target_page = None
            for p in all_classified:
                if p.get("detected_type") == target_type:
                    target_page = p
                    break
                    
            if target_page and all_pages_images:
                pdf_name = target_page["pdf_name"]
                page_idx = target_page["page_index"]
                src_imgs = all_pages_images.get(pdf_name, [])
                if page_idx < len(src_imgs):
                    st.markdown("##### 🎨 Visual Takeoff Shading (معاينة التظليل البصري للكميات المكتشفة)")
                    img_arr = src_imgs[page_idx]
                    
                    # Call OpenCV to detect room/wall boundaries to display as overlays
                    ppm = st.session_state.get("pixels_per_meter", 100.0)
                    from pdf_engine.element_detector import detect_rooms, detect_walls, detect_columns
                    
                    rooms_geom = detect_rooms(img_arr, ppm)
                    walls_geom = detect_walls(img_arr, ppm)
                    columns_geom = detect_columns(img_arr, ppm)
                    
                    from utils.canvas_component import render_interactive_canvas
                    render_interactive_canvas(img_arr, rooms=rooms_geom, walls=walls_geom, columns=columns_geom, width=800, height=600)
                    
            confirmed_data[fk] = fdata

    # ── Sub-Structure review ──
    sub_data = auto_state.get("auto_substructure", {})
    with st.expander("️ Foundation & Sub-Structure | الأساسات", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        sub_data["tb_width"]  = col_a.number_input(
            "Tie Beam Width (m)",  min_value=0.0, step=0.05,
            value=float(sub_data.get("tb_width",  0.30)), key="rev_tbw")
        sub_data["tb_depth"]  = col_b.number_input(
            "Tie Beam Depth (m)",  min_value=0.0, step=0.05,
            value=float(sub_data.get("tb_depth",  0.50)), key="rev_tbd")
        sub_data["tb_length"] = col_c.number_input(
            "Tie Beam Length (m)", min_value=0.0, step=1.0,
            value=float(sub_data.get("tb_length", 0.0)),  key="rev_tbl")

        if sub_data.get("foundations"):
            st.markdown("**Foundations:**")
            found_df = pd.DataFrame(sub_data["foundations"])
            edited   = st.data_editor(
                found_df, key="rev_found", use_container_width=True, num_rows="dynamic"
            )
            sub_data["foundations"] = edited.to_dict("records") if edited is not None else sub_data["foundations"]

        if sub_data.get("neck_columns"):
            st.markdown("**Neck Columns:**")
            nc_df  = pd.DataFrame(sub_data["neck_columns"])
            edited = st.data_editor(
                nc_df, key="rev_nc", use_container_width=True, num_rows="dynamic"
            )
            sub_data["neck_columns"] = edited.to_dict("records") if edited is not None else sub_data["neck_columns"]

    confirmed_data["substructure"] = sub_data

    # ── Confirm ──
    st.markdown("---")
    if st.button(
        "Confirm All & Calculate BOQ | تأكيد وحساب الكميات",
        type="primary",
        key="btn_confirm_all",
    ):
        st.session_state["confirmed_auto_data"] = confirmed_data
        st.session_state["use_auto_data"]       = True

        # Push values into the individual tab session_state keys so the
        # Sub-Structure and Finishes tabs pick them up immediately
        _push_to_finishes_state(confirmed_data)
        _push_to_substructure_state(confirmed_data.get("substructure", {}))

        st.success("Confirmed! Go to BOQ Summary tab to see your quantities.")

    return confirmed_data
