import streamlit as st
import pandas as pd
from engine.substructure import calc_all_substructure


_DEFAULT_FOUNDATIONS = [
    {"type_label": "F1", "width": 1.5, "length": 1.5, "depth": 0.5, "count": 1}
]
_DEFAULT_NECK_COLS = [
    {"type_label": "NC1", "width": 0.3, "length": 0.3, "count": 1}
]


def _init_state():
    if "sub_foundations" not in st.session_state:
        st.session_state["sub_foundations"] = pd.DataFrame(_DEFAULT_FOUNDATIONS)
    if "sub_neck_cols" not in st.session_state:
        st.session_state["sub_neck_cols"] = pd.DataFrame(_DEFAULT_NECK_COLS)
    for key, default in [("sub_tb_width", 0.3), ("sub_tb_depth", 0.5), ("sub_tb_length", 0.0)]:
        if key not in st.session_state:
            st.session_state[key] = default


def render_substructure_tab(project: dict) -> dict:
    _init_state()

    st.subheader("️ Sub-Structure | الأعمال تحت الأرض")

    # ── Foundations ──
    st.markdown("#### Isolated Foundations | الأساسات المنفردة")
    found_df = st.data_editor(
        st.session_state["sub_foundations"],
        num_rows="dynamic",
        use_container_width=True,
        key="de_foundations",
        column_config={
            "type_label": st.column_config.TextColumn("Type | النوع", width="small"),
            "width":      st.column_config.NumberColumn("Width (m)", min_value=0.0, step=0.05, format="%.2f"),
            "length":     st.column_config.NumberColumn("Length (m)", min_value=0.0, step=0.05, format="%.2f"),
            "depth":      st.column_config.NumberColumn("Depth (m)", min_value=0.0, step=0.05, format="%.2f"),
            "count":      st.column_config.NumberColumn("Count | العدد", min_value=0, step=1, format="%d"),
        },
    )
    st.session_state["sub_foundations"] = found_df

    # ── Neck Columns ──
    st.markdown("#### Neck Columns | أعمدة الرقبة")
    neck_df = st.data_editor(
        st.session_state["sub_neck_cols"],
        num_rows="dynamic",
        use_container_width=True,
        key="de_neck_cols",
        column_config={
            "type_label": st.column_config.TextColumn("Type | النوع", width="small"),
            "width":      st.column_config.NumberColumn("Width (m)", min_value=0.0, step=0.05, format="%.2f"),
            "length":     st.column_config.NumberColumn("Length (m)", min_value=0.0, step=0.05, format="%.2f"),
            "count":      st.column_config.NumberColumn("Count | العدد", min_value=0, step=1, format="%d"),
        },
    )
    st.session_state["sub_neck_cols"] = neck_df

    # ── Tie Beam ──
    st.markdown("#### Tie Beam | الميدة")
    c1, c2, c3 = st.columns(3)
    with c1:
        tb_width = st.number_input("TB Width (m)", min_value=0.0, step=0.05,
                                   value=float(st.session_state["sub_tb_width"]), key="ni_tb_width")
        st.session_state["sub_tb_width"] = tb_width
    with c2:
        tb_depth = st.number_input("TB Depth (m)", min_value=0.0, step=0.05,
                                   value=float(st.session_state["sub_tb_depth"]), key="ni_tb_depth")
        st.session_state["sub_tb_depth"] = tb_depth
    with c3:
        tb_length = st.number_input("TB Total Length (m)", min_value=0.0, step=0.5,
                                    value=float(st.session_state["sub_tb_length"]), key="ni_tb_length")
        st.session_state["sub_tb_length"] = tb_length

    # ── Build data dict ──
    foundations_list = found_df.to_dict("records") if not found_df.empty else []
    neck_cols_list   = neck_df.to_dict("records") if not neck_df.empty else []

    data = {
        "foundations":    foundations_list,
        "neck_columns":   neck_cols_list,
        "tb_width":       tb_width,
        "tb_depth":       tb_depth,
        "tb_length":      tb_length,
        "ext_perimeter":  project.get("ext_perimeter", 0.0),
        "gf_area":        project.get("gf_area", 0.0),
        "longest_length": project.get("longest_length", 0.0),
        "longest_width":  project.get("longest_width", 0.0),
    }

    # ── Live Results Preview ──
    st.markdown("---")
    st.markdown("#### Live Results Preview | نتائج مباشرة")
    results = calc_all_substructure(data)
    preview_rows = [{"Item": en, "البيان": ar, "Unit": unit, "Quantity": round(qty, 2)}
                    for key, (qty, unit, en, ar) in results.items()]
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    return data
