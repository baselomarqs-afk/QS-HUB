"""
STEP 4 — Confirm Missing Values
User confirms values AI couldn't find:
- Excavation depth (always ask)
- Road base (yes/no)
- Floor heights (if not seen)
- Number of levels (if not seen)
"""
import streamlit as st
from workflow.workflow_state import mark_step_done


from utils.i18n import t

def render_step4() -> bool:
    st.markdown(t("confirm_title"))
    st.caption(t("confirm_caption"))

    # Force sync disk files with session state
    if "extraction_results" in st.session_state:
        from workflow.step3_extract import merge_schedule_json_to_results
        merge_schedule_json_to_results(st.session_state["extraction_results"])

    results = st.session_state.get("extraction_results", {})

    # ── Always ask ──
    st.markdown("### ️ Sub-Structure Constants | ثوابت تحت الأرض")

    col1, col2 = st.columns(2)
    with col1:
        exc_depth = st.number_input(
            "Excavation Depth (m) | عمق الحفر",
            min_value=0.5, max_value=5.0,
            value=float(st.session_state.get("excavation_depth", 1.25)),
            step=0.05,
            help="Default: 1.25m — change if your project is different"
        )
        st.session_state["excavation_depth"] = exc_depth

    with col2:
        road_base = st.radio(
            "Include Road Base? | هل يوجد رمل مدموك؟",
            options=["Yes | نعم", "No | لا"],
            index=0 if st.session_state.get("include_road_base", True) else 1,
            key="road_base_radio"
        )
        st.session_state["include_road_base"] = road_base.startswith("Yes")

    st.divider()

    # ── Floor heights — check if AI found them ──
    st.markdown("###  Floor Heights | ارتفاعات الأدوار")

    found_gf_h = _get_from_results(results, "ground_floor_plan", "floor_height")
    found_f1_h = _get_from_results(results, "first_floor_plan",  "floor_height")
    found_f2_h = _get_from_results(results, "second_floor_plan", "floor_height")

    col1, col2, col3 = st.columns(3)
    with col1:
        gf_h = st.number_input(
            f"GF Height (m) {' AI found' if found_gf_h else ' Enter manually'}",
            value=float(found_gf_h or st.session_state.get("gf_height", 4.0)),
            min_value=2.5, max_value=6.0, step=0.1, key="conf_gf_h"
        )
        st.session_state["gf_height"] = gf_h

    with col2:
        f1_h = st.number_input(
            f"1F Height (m) {' AI found' if found_f1_h else ' Enter manually'}",
            value=float(found_f1_h or st.session_state.get("f1_height", 4.0)),
            min_value=2.5, max_value=6.0, step=0.1, key="conf_f1_h"
        )
        st.session_state["f1_height"] = f1_h

    with col3:
        f2_h = st.number_input(
            f"2F Height (m) {' AI found' if found_f2_h else ' Enter manually'}",
            value=float(found_f2_h or st.session_state.get("f2_height", 4.0)),
            min_value=2.5, max_value=6.0, step=0.1, key="conf_f2_h"
        )
        st.session_state["f2_height"] = f2_h

    st.divider()

    # ── Number of levels ──
    st.markdown("### ️ Building Levels | عدد الأدوار")

    found_levels = _get_from_results(results, "slab_1st", "structural_levels")

    num_floors = st.selectbox(
        f"Number of Floors {' AI found' if found_levels else ' Select manually'}",
        options=[1, 2, 3, 4],
        index=int(found_levels - 1) if found_levels else st.session_state.get("num_floors_idx", 1),
        format_func=lambda x: {1: "Ground Floor Only (G-Only)", 2: "Ground + 1 Floor (G+1)", 3: "Ground + 2 Floors (G+2)", 4: "Ground + 3 Floors (G+3)"}.get(x, f"{x} Floors"),
        key="conf_levels"
    )
    st.session_state["num_floors"]     = num_floors
    st.session_state["num_floors_idx"] = num_floors - 1

    st.divider()

    # ── Floor areas (drive ALL finishes) — confirm if AI missed them ──────────
    st.markdown("###  Floor areas | مساحات الأدوار")
    st.caption("These drive every finish item. AI pre-fills from the plans — "
               "correct any that are wrong / zero.")
    _PLAN = {"gf": "ground_floor_plan", "1f": "first_floor_plan", "2f": "second_floor_plan"}
    _SLAB = {"gf": "slab_1st", "1f": "slab_2nd", "2f": "roof_slab"}
    _LBL  = {"gf": "Ground Floor | الدور الأرضي", "1f": "1st Floor | الدور الأول", "2f": "2nd Floor | الدور الثاني"}
    
    for fk in ["gf", "1f", "2f"][:num_floors]:
        ai_area = _get_from_results(results, _PLAN[fk], "total_floor_area") or 0.0
        ai_wet  = _get_from_results(results, _PLAN[fk], "wet_area") or 0.0
        ai_thk  = _get_from_results(results, _SLAB[fk], "slab_thickness") or 0.20
        ai_ext  = _get_from_results(results, _PLAN[fk], "ext_perimeter") or (
            _get_from_results(results, "tie_beam", "ext_perimeter") if fk == "gf" else 0.0
        ) or 0.0
        ai_int  = _get_from_results(results, _PLAN[fk], "int_walls_length") or 0.0
        
        st.markdown(f"#### {_LBL[fk]}")
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.0])
        c1.number_input(f"Floor Area (m²) | المساحة",
                        0.0, 3000.0, float(st.session_state.get(f"ci_area_{fk}", ai_area) or ai_area),
                        step=1.0, key=f"ci_area_{fk}")
        c2.number_input(f"Wet Area (m²) | المساحة الرطبة",
                        0.0, 800.0, float(st.session_state.get(f"ci_wet_{fk}", ai_wet) or ai_wet),
                        step=1.0, key=f"ci_wet_{fk}")
        c3.number_input(f"Ext. Perimeter (m) | المحيط الخارجي",
                        0.0, 500.0, float(st.session_state.get(f"ci_ext_{fk}", ai_ext) or ai_ext),
                        step=0.5, key=f"ci_ext_{fk}", help="External wall perimeter of this floor")
        c4.number_input(f"Int. Walls (m) | الجدران الداخلية",
                        0.0, 1000.0, float(st.session_state.get(f"ci_int_{fk}", ai_int) or ai_int),
                        step=0.5, key=f"ci_int_{fk}", help="Total internal partition wall length of this floor")
        c5.number_input(f"Slab Thk (m) | سمك البلاطة",
                        0.10, 0.50, float(st.session_state.get(f"ci_thk_{fk}", ai_thk) or ai_thk),
                        step=0.01, key=f"ci_thk_{fk}", help="Suspended slab thickness for concrete volume")
        st.write("")

    st.divider()

    # ── Setting Out — ALWAYS required (AI rarely finds these) ─────────────────
    st.markdown("### ️ Setting Out | أعمال الموقع")
    st.caption("Required for Interlock Paving and Compound Wall — enter from the site plan / title block.")

    ai_plot      = _get_from_results(results, "setting_out", "plot_area")      or 0.0
    ai_compound  = _get_from_results(results, "setting_out", "compound_length") or 0.0

    col_so1, col_so2 = st.columns(2)
    with col_so1:
        plot_area = st.number_input(
            "Plot Area (m²) | مساحة الأرض",
            min_value=0.0, max_value=10000.0,
            value=float(st.session_state.get("plot_area", ai_plot) or ai_plot),
            step=1.0,
            help="Total land area — used to calculate Interlock Paving = Plot Area − GF Area",
        )
        st.session_state["plot_area"] = plot_area

    with col_so2:
        compound_length = st.number_input(
            "Compound Wall Length (m) | طول سور الموقع",
            min_value=0.0, max_value=500.0,
            value=float(st.session_state.get("compound_length", ai_compound) or ai_compound),
            step=0.5,
            help="Total perimeter of the boundary wall around the plot",
        )
        st.session_state["compound_length"] = compound_length

    # Show live preview
    gf_area_preview = _get_from_results(results, "ground_floor_plan", "total_floor_area") \
                      or float(st.session_state.get("ci_area_gf", 0) or 0)
    interlock_preview = max(plot_area - gf_area_preview, 0)
    st.info(
        f" Interlock preview: **{plot_area:.0f} − {gf_area_preview:.0f} = {interlock_preview:.0f} m²** &nbsp;|&nbsp; "
        f" Compound Wall: **{compound_length:.1f} m**",
        icon=None
    )

    st.divider()

    st.caption("ℹ️ Detailed schedule values (footings, beams, columns) are "
               "reviewed & edited in **Step 6 — Review Results**.")

    if st.button(t("confirm_next_btn"), type="primary", use_container_width=True):
        mark_step_done("confirm")
        return True

    return False


def _get_from_results(results: dict, drawing_type: str, field: str):
    for r in results.values():
        if r.get("drawing_type") == drawing_type:
            val = r.get(field)
            if val is not None:
                return val
    return None


def _find_missing_values(results: dict) -> list:
    from engine.dimension_filter import DRAWING_REQUIRED_INPUTS
    # Fields that are stored as lists in the AI response rather than flat scalars.
    # If the list exists and is non-empty, the field is NOT missing.
    _LIST_COVERS = {
        # foundation flat keys → covered by footings list
        "footing_width":  ("footings",),
        "footing_length": ("footings",),
        "footing_depth":  ("footings",),
        "footing_count":  ("footings",),
        # slab flat keys → covered by beams list
        "beam_length":    ("beams",),
        "beam_width":     ("beams",),
        "beam_depth":     ("beams",),
        # column flat keys → covered by columns list
        "col_width":      ("columns",),
        "col_length":     ("columns",),
        "col_count":      ("columns",),
        "nc_width":       ("columns",),
        "nc_length":      ("columns",),
        "nc_count":       ("columns",),
        # schedule flat keys → covered by doors/windows lists
        "door_count":     ("doors",),
        "win_width":      ("windows",),
        "win_height":     ("windows",),
        "win_count":      ("windows",),
    }

    missing = []
    seen = set()   # dedupe: same drawing_type may appear on several pages
    for key, data in results.items():
        if not data.get("_ok"):
            continue
        drawing_type = data.get("drawing_type", "unknown")
        config = DRAWING_REQUIRED_INPUTS.get(drawing_type, {})
        for field in config.get("extract_only", []):
            mkey = f"{drawing_type}_{field}"
            if mkey in seen:
                continue
            # Check flat key first
            if data.get(field) is not None:
                continue
            # Check if a list-based field covers this flat key
            list_names = _LIST_COVERS.get(field, ())
            covered = any(
                isinstance(data.get(ln), list) and len(data.get(ln, [])) > 0
                for ln in list_names
            )
            if covered:
                continue
            seen.add(mkey)
            missing.append({
                "key":          mkey,
                "label":        field.replace("_", " ").title(),
                "drawing":      drawing_type.replace("_", " ").title(),
                "drawing_type": drawing_type,
            })
    return missing
