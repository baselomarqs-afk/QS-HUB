"""
STEP 6 — Review Results
Show sub, super, arch results separately
User can edit any value before BOQ
"""
import streamlit as st
import pandas as pd
import threading
from workflow.workflow_state import mark_step_done
from utils.i18n import t
from utils.db import get_connection

def save_correction_to_db(user_id, section, item_key, original, corrected):
    """Save user corrections to the database for AI learning."""
    if not user_id:
        return
    def _save():
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO qto_ai_corrections (user_id, drawing_type, item_key, original_value, corrected_value) VALUES (%s, %s, %s, %s, %s)",
                        (user_id, section, item_key, str(original), str(corrected))
                    )
                conn.commit()
        except Exception as e:
            print(f"Failed to save correction: {e}")
    threading.Thread(target=_save, daemon=True).start()

def get_section_confidence(section: str) -> str:
    """Heuristic to determine confidence based on source pages."""
    res = st.session_state.get("extraction_results", {})
    deps = []
    if section == "sub": deps = ["foundation_plan", "tie_beam_plan"]
    elif section == "sup": deps = ["ground_columns", "upper_columns", "ground_floor_plan", "first_floor_plan", "roof_plan"]
    elif section == "fin": deps = ["ground_floor_plan", "first_floor_plan"]
    elif section == "open": deps = ["window_schedule", "door_schedule"]
    
    # If no results at all, assume low
    if not res: return "⚠️"
    
    for r in res.values():
        if r.get("drawing_type") in deps:
            if r.get("confidence") in ["low", "medium"]:
                return "⚠️" # Yellow/Warning
    return "✅" # Green/High confidence


def render_step6() -> bool:
    st.markdown(t("review_title"))
    st.caption("Review calculated quantities. Edit any incorrect values before BOQ. ✅ = High Confidence, ⚠️ = Needs Review (Low/Med Confidence)")

    sub    = st.session_state.get("sub_results", {})
    sup    = st.session_state.get("super_results", {})
    fin    = st.session_state.get("finish_results", {})
    opens  = st.session_state.get("opening_results", {})
    setout = st.session_state.get("setting_out", {})
    
    user_id = st.session_state.get("user", {}).get("id")

    tabs = st.tabs([
        f"️ {t('substructure')}",
        f" {t('superstructure')}",
        f" {t('finishes')}",
        f" {t('openings')} & Site",
    ])

    def show_results(data: dict, section_key: str):
        icon = get_section_confidence(section_key)
        rows = []
        for key, val in data.items():
            if isinstance(val, tuple):
                qty, unit, en, ar = val
                rows.append({"Item": en, "البند": ar, "Unit": unit, "Qty": round(float(qty), 2), "key": key})

        if not rows:
            st.info("No data yet.")
            return

        for row in rows:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
            col1.markdown(f"**{row['Item']}** {icon}")
            col2.markdown(row["البند"])
            col3.markdown(f"`{row['Unit']}`")
            edited = col4.number_input(
                t("quantity"), value=row["Qty"], step=0.1,
                key=f"edit_{section_key}_{row['key']}",
                label_visibility="collapsed"
            )
            # Update if changed
            if edited != row["Qty"] and row["key"] in data:
                save_correction_to_db(user_id, section_key, row["key"], row["Qty"], edited)
                old = data[row["key"]]
                if isinstance(old, tuple):
                    data[row["key"]] = (edited, old[1], old[2], old[3])

    with tabs[0]:
        show_results(sub, "sub")
        st.session_state["sub_results"] = sub

    with tabs[1]:
        show_results(sup, "sup")
        st.session_state["super_results"] = sup

    with tabs[2]:
        icon = get_section_confidence("fin")
        num_floors = st.session_state.get("num_floors", 2)
        floor_keys = ["gf", "f1", "f2"][:num_floors]
        floor_labels = {"gf": t("ground_floor"), "f1": t("first_floor"), "f2": t("second_floor")}
        for fk in floor_keys:
            st.markdown(f"#### {floor_labels[fk]} {icon}")
            fres = fin.get(fk, {})
            for field, val in fres.items():
                if isinstance(val, (int, float)):
                    new_val = st.number_input(
                        field.replace("_", " ").title(),
                        value=round(float(val), 2),
                        step=0.1,
                        key=f"edit_fin_{fk}_{field}"
                    )
                    if new_val != round(float(val), 2):
                        save_correction_to_db(user_id, "fin", f"{fk}_{field}", val, new_val)
                    fres[field] = new_val
        st.session_state["finish_results"] = fin

    with tabs[3]:
        icon = get_section_confidence("open")
        st.markdown(f"### 🚪 Openings & Site Setting Out | الفتحات وأعمال الموقع {icon}")
        st.caption("You can override any calculated quantity below directly / يمكنك تعديل أي كمية محسوبة أدناه مباشرة:")
        
        # 1. Total Doors
        edited_doors = st.number_input(
            "Total Doors | إجمالي الأبواب (Nr)",
            min_value=0.0, max_value=500.0,
            value=float(opens.get("doors", 0)),
            step=1.0,
            key="edit_open_doors",
            help="Total count of all doors in the project"
        )
        if edited_doors != opens.get("doors", 0):
            save_correction_to_db(user_id, "open", "doors", opens.get("doors", 0), edited_doors)
            opens["doors"] = edited_doors
            st.session_state["opening_results"] = opens
            
        # 2. Total Window Area
        edited_windows = st.number_input(
            "Total Window Area | إجمالي مساحة النوافذ (m²)",
            min_value=0.0, max_value=1000.0,
            value=float(opens.get("windows", 0)),
            step=0.1,
            key="edit_open_windows",
            help="Total area of all windows in the project"
        )
        if edited_windows != opens.get("windows", 0):
            save_correction_to_db(user_id, "open", "windows", opens.get("windows", 0), edited_windows)
            opens["windows"] = edited_windows
            st.session_state["opening_results"] = opens

        # 3. Interlock Paving
        edited_interlock = st.number_input(
            "Interlock Paving | رصف إنترلوك (m²)",
            min_value=0.0, max_value=10000.0,
            value=float(setout.get("interlock", 0)),
            step=1.0,
            key="edit_setout_interlock",
            help="Total interlock area = Plot Area - Ground Floor Area"
        )
        if edited_interlock != setout.get("interlock", 0):
            save_correction_to_db(user_id, "setout", "interlock", setout.get("interlock", 0), edited_interlock)
            setout["interlock"] = edited_interlock
            st.session_state["setting_out"] = setout
            
        # 4. Compound Wall
        edited_compound = st.number_input(
            "Compound Wall | سور الموقع (m)",
            min_value=0.0, max_value=1000.0,
            value=float(setout.get("compound_wall", 0)),
            step=0.5,
            key="edit_setout_compound",
            help="Total perimeter length of the compound boundary wall"
        )
        if edited_compound != setout.get("compound_wall", 0):
            save_correction_to_db(user_id, "setout", "compound_wall", setout.get("compound_wall", 0), edited_compound)
            setout["compound_wall"] = edited_compound
            st.session_state["setting_out"] = setout

    st.divider()
    
    # --- AI Learning / Memory Hook ---
    with st.expander("🧠 Teach AI (AI Memory & Vocabulary)", expanded=False):
        st.markdown("Did the AI misclassify an abbreviation from the CAD drawings? Teach it the correct mapping for your future projects!")
        mc1, mc2, mc3 = st.columns([2, 2, 1])
        with mc1:
            mem_orig = st.text_input("If AI sees this (e.g., 'T.B' or 'Neck_col'):", key="mem_orig")
        with mc2:
            mem_map = st.text_input("It should always classify it as:", key="mem_map")
        with mc3:
            st.write("")
            st.write("")
            if st.button("Teach AI", type="secondary", use_container_width=True):
                if mem_orig and mem_map and user_id:
                    try:
                        from engine.qto_memory import record_mapping
                        record_mapping(user_id, mem_orig, mem_map)
                        st.success(f"Learned: {mem_orig} ➔ {mem_map}")
                    except Exception as e:
                        st.error(f"Error saving rule: {e}")
                elif not user_id:
                    st.warning("Please log in to save personalized AI rules.")
                else:
                    st.warning("Please fill both fields.")

    st.divider()
    if st.button(t("review_next_btn"), type="primary", use_container_width=True):
        project_name = st.session_state.get("project_name", "Villa Project")
        if not st.session_state.get(f"auto_saved_{project_name}"):
            from utils.usage import EVENT_PROJECT, log_usage
            if user_id:
                log_usage(user_id, EVENT_PROJECT, metadata={"project_name": project_name})
            st.session_state[f"auto_saved_{project_name}"] = True
            
        mark_step_done("review")
        return True

    return False
