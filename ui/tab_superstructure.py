import streamlit as st
import pandas as pd
from engine.superstructure import calc_all_superstructure


_FLOOR_LABELS = {
    "gf":   "Ground Floor → 1st Slab | الأرضي",
    "f1":   "1st Floor → 2nd Slab | الأول",
    "f2":   "2nd Floor → Roof Slab | الثاني",
    "roof": "Roof Level | السطح",
}

_DEFAULT_BEAMS   = [{"label": "B1", "length": 5.0, "width": 0.25, "depth": 0.50}]
_DEFAULT_COLUMNS = [{"label": "C1", "length": 0.30, "width": 0.30, "count": 1}]


def _init_floor_state(fk: str):
    if f"super_{fk}_thickness" not in st.session_state:
        st.session_state[f"super_{fk}_thickness"] = 0.20
    if f"super_{fk}_beams" not in st.session_state:
        st.session_state[f"super_{fk}_beams"] = pd.DataFrame(_DEFAULT_BEAMS)
    if f"super_{fk}_columns" not in st.session_state:
        st.session_state[f"super_{fk}_columns"] = pd.DataFrame(_DEFAULT_COLUMNS)
    if f"super_roof_perimeter" not in st.session_state:
        st.session_state["super_roof_perimeter"] = 0.0


def _render_floor_section(fk: str, slab_area: float) -> dict:
    _init_floor_state(fk)

    label = _FLOOR_LABELS.get(fk, fk)
    st.markdown(f"##### {label}")

    col1, col2 = st.columns([1, 3])
    with col1:
        thickness = st.number_input(
            f"Slab Thickness (m) — {fk}",
            min_value=0.10, max_value=0.50, step=0.01,
            value=float(st.session_state[f"super_{fk}_thickness"]),
            key=f"ni_super_{fk}_thk",
        )
        st.session_state[f"super_{fk}_thickness"] = thickness
        st.metric("Slab Area (from sidebar)", f"{slab_area:.2f} m²")

    with col2:
        st.markdown("**Beams | الكمرات**")
        beams_df = st.data_editor(
            st.session_state[f"super_{fk}_beams"],
            num_rows="dynamic",
            use_container_width=True,
            key=f"de_super_{fk}_beams",
            column_config={
                "label":  st.column_config.TextColumn("Label", width="small"),
                "length": st.column_config.NumberColumn("Length (m)", min_value=0.0, step=0.1, format="%.2f"),
                "width":  st.column_config.NumberColumn("Width (m)",  min_value=0.0, step=0.05, format="%.2f"),
                "depth":  st.column_config.NumberColumn("Depth (m)",  min_value=0.0, step=0.05, format="%.2f"),
            },
        )
        st.session_state[f"super_{fk}_beams"] = beams_df

        st.markdown("**Columns | الأعمدة**")
        cols_df = st.data_editor(
            st.session_state[f"super_{fk}_columns"],
            num_rows="dynamic",
            use_container_width=True,
            key=f"de_super_{fk}_cols",
            column_config={
                "label":  st.column_config.TextColumn("Label", width="small"),
                "length": st.column_config.NumberColumn("Length (m)", min_value=0.0, step=0.05, format="%.2f"),
                "width":  st.column_config.NumberColumn("Width (m)",  min_value=0.0, step=0.05, format="%.2f"),
                "count":  st.column_config.NumberColumn("Count",      min_value=0,   step=1,    format="%d"),
            },
        )
        st.session_state[f"super_{fk}_columns"] = cols_df

    return {
        "slab_area":       slab_area,
        "slab_thickness":  thickness,
        "beams":           beams_df.to_dict("records") if not beams_df.empty else [],
        "columns":         cols_df.to_dict("records") if not cols_df.empty else [],
    }


def render_superstructure_tab(project: dict) -> dict:
    st.subheader(" Super-Structure | الأعمال العلوية")

    num_floors = project.get("num_floors", 2)
    floor_areas = {
        "gf":   project.get("gf_area", 0.0),
        "f1":   project.get("f1_area", 0.0),
        "f2":   project.get("f2_area", 0.0),
    }

    floor_keys = ["gf", "f1", "f2"][:num_floors]
    data = {}

    for fk in floor_keys:
        data[fk] = _render_floor_section(fk, float(floor_areas.get(fk, 0.0)))
        st.divider()

    # ── Roof ──
    _init_floor_state("roof")
    st.markdown("##### Roof Level | مستوى السطح")
    roof_perimeter = st.number_input(
        "Roof Perimeter (m) — for parapet (auto from sidebar if set)",
        min_value=0.0, step=0.5,
        value=float(project.get("roof_perimeter", st.session_state.get("super_roof_perimeter", 0.0))),
        key="ni_super_roof_per",
    )
    st.session_state["super_roof_perimeter"] = roof_perimeter

    roof_section = _render_floor_section("roof", float(project.get("roof_area", 0.0)))
    roof_section["roof_perimeter"] = roof_perimeter
    data["roof"] = roof_section

    # ── Live Results Preview ──
    st.markdown("---")
    st.markdown("#### Live Results Preview | نتائج مباشرة")
    results = calc_all_superstructure(data, num_floors)
    preview_rows = [{"Item": en, "البيان": ar, "Unit": unit, "Quantity": round(qty, 2)}
                    for key, (qty, unit, en, ar) in results.items()]
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    return data
