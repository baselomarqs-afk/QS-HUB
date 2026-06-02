"""
STEP 7 — Arrange BOQ
User can add items, reorder, add pricing (optional)
"""
import streamlit as st
import pandas as pd
from engine.boq_builder import build_boq_dataframe
from workflow.workflow_state import mark_step_done
from utils.i18n import t

def render_step7() -> bool:
    st.markdown(t("arrange_title"))

    sub    = st.session_state.get("sub_results", {})
    sup    = st.session_state.get("super_results", {})
    fin    = st.session_state.get("finish_results", {})
    opens  = st.session_state.get("opening_results", {})
    setout = st.session_state.get("setting_out", {})
    num_fl = st.session_state.get("num_floors", 2)

    # Build BOQ
    boq_df = build_boq_dataframe(sub, sup, fin, opens, num_fl, setout)
    st.session_state["boq_df"] = boq_df
    
    project_name = st.session_state.get("project_name", "Villa Project")
    user = st.session_state.get("user", {})
    
    # Auto-save after generating BOQ
    if not st.session_state.get(f"auto_saved_boq_{project_name}"):
        from utils.state_recovery import save_project_state
        if user and user.get("id"):
            save_project_state(user["id"])
        st.session_state[f"auto_saved_boq_{project_name}"] = True

    display = boq_df[boq_df["_is_header"] == False].copy()
    headers = boq_df[boq_df["_is_header"] == True].copy()

    st.success(f" {len(display)} items | {len(headers)} sections")

    # Optional pricing
    add_pricing = st.toggle(" Add Unit Rates (Optional) | أضف الأسعار", value=False)

    show_cols = ["#", "Description (English)", "البيان", "Unit", "Quantity"]
    if add_pricing:
        if "Rate" not in display.columns:
            display["Rate"] = 0.0
            display["Total"] = 0.0
        show_cols += ["Rate", "Total"]

        edited = st.data_editor(
            display[show_cols],
            use_container_width=True,
            height=500,
            column_config={
                "Rate":  st.column_config.NumberColumn("Rate (AED)", min_value=0, format="%.2f"),
                "Total": st.column_config.NumberColumn("Total (AED)", disabled=True, format="%.2f"),
            },
            key="boq_editor"
        )
        if edited is not None:
            edited["Total"] = edited["Quantity"] * edited["Rate"]
            st.metric(" Grand Total (AED)", f"{edited['Total'].sum():,.2f}")
            st.session_state["boq_priced"] = edited
    else:
        st.dataframe(
            display[show_cols],
            use_container_width=True,
            height=500,
        )

    # Add custom item
    st.markdown("### ➕ Add Custom Item | أضف بند يدوي")
    with st.expander("Add Item"):
        col1, col2, col3, col4 = st.columns(4)
        new_en  = col1.text_input("Description (EN)", key="new_en")
        new_ar  = col2.text_input("البيان", key="new_ar")
        new_unit= col3.text_input("Unit", key="new_unit")
        new_qty = col4.number_input("Qty", min_value=0.0, key="new_qty")
        if st.button("➕ Add") and new_en:
            custom = st.session_state.get("custom_items", [])
            custom.append({"en": new_en, "ar": new_ar, "unit": new_unit, "qty": new_qty})
            st.session_state["custom_items"] = custom
            st.success(f"Added: {new_en}")

    if st.button(t("arrange_next_btn"), type="primary", use_container_width=True):
        mark_step_done("arrange")
        return True

    return False
