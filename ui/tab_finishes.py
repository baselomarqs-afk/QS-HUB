import streamlit as st
import pandas as pd
from engine.finishes import calc_villa_finishes


_FLOOR_LABELS = {
    "gf": "Ground Floor | الدور الأرضي",
    "f1": "1st Floor | الدور الأول",
    "f2": "2nd Floor | الدور الثاني",
}

_FINISH_KEYS = [
    ("thermal_block", "Thermal Block (Ext.)", "بلوك حراري",  "m²"),
    ("int_block",     "Internal Block Work",  "بلوك داخلي",  "m²"),
    ("dry_floor",     "Dry Area Flooring",    "بلاط جاف",    "m²"),
    ("wet_floor",     "Wet Area Flooring",    "بلاط رطب",    "m²"),
    ("wall_tiles",    "Wall Tiles",           "بلاط جدران",  "m²"),
    ("skirting",      "Skirting",             "قرنيش",       "m"),
    ("int_paint",     "Internal Paint",       "دهان داخلي",  "m²"),
    ("int_plaster",   "Internal Plaster",     "لياسة داخلية","m²"),
    ("dry_ceiling",   "Dry Ceiling",          "سقف جاف",     "m²"),
    ("wet_ceiling",   "Wet Ceiling",          "سقف رطب",     "m²"),
    ("balcony_wp",    "Balcony Waterproofing","عزل بلكونة",  "m²"),
]


def _init_floor_state(fk: str):
    defaults = {
        f"fin_{fk}_wet_area":        0.0,
        f"fin_{fk}_wet_perimeter":   0.0,
        f"fin_{fk}_dry_perimeter":   0.0,
        f"fin_{fk}_int_walls_length":0.0,
        f"fin_{fk}_balcony_area":    0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _render_floor_inputs(fk: str, floor_area: float, floor_height: float) -> dict:
    _init_floor_state(fk)

    label = _FLOOR_LABELS.get(fk, fk)
    st.markdown(f"##### {label}")
    st.caption(f"Floor area from sidebar: **{floor_area:.2f} m²** | Floor height: **{floor_height:.1f} m**")

    c1, c2, c3 = st.columns(3)
    with c1:
        wet_area = st.number_input(
            "Wet Area (m²) | المساحة الرطبة", min_value=0.0, step=1.0,
            value=float(st.session_state[f"fin_{fk}_wet_area"]), key=f"ni_fin_{fk}_wet_area",
        )
        st.session_state[f"fin_{fk}_wet_area"] = wet_area

        wet_perimeter = st.number_input(
            "Wet Perimeter (m) | محيط الرطب", min_value=0.0, step=0.5,
            value=float(st.session_state[f"fin_{fk}_wet_perimeter"]), key=f"ni_fin_{fk}_wet_per",
        )
        st.session_state[f"fin_{fk}_wet_perimeter"] = wet_perimeter

    with c2:
        dry_perimeter = st.number_input(
            "Dry Perimeter (m) | محيط الجاف", min_value=0.0, step=0.5,
            value=float(st.session_state[f"fin_{fk}_dry_perimeter"]), key=f"ni_fin_{fk}_dry_per",
        )
        st.session_state[f"fin_{fk}_dry_perimeter"] = dry_perimeter

        int_walls_length = st.number_input(
            "Int. Walls Length (m) | طول الجدران الداخلية", min_value=0.0, step=0.5,
            value=float(st.session_state[f"fin_{fk}_int_walls_length"]), key=f"ni_fin_{fk}_int_walls",
        )
        st.session_state[f"fin_{fk}_int_walls_length"] = int_walls_length

    with c3:
        balcony_area = st.number_input(
            "Balcony Area (m²) | مساحة البلكونة", min_value=0.0, step=0.5,
            value=float(st.session_state[f"fin_{fk}_balcony_area"]), key=f"ni_fin_{fk}_balcony",
        )
        st.session_state[f"fin_{fk}_balcony_area"] = balcony_area

    return {
        "floor_area":       floor_area,
        "wet_area":         wet_area,
        "wet_perimeter":    wet_perimeter,
        "dry_perimeter":    dry_perimeter,
        "int_walls_length": int_walls_length,
        "balcony_area":     balcony_area,
        "height":           floor_height,
    }


def render_finishes_tab(project: dict) -> dict:
    st.subheader(" Finishes | التشطيبات")

    num_floors   = project.get("num_floors", 2)
    floor_keys   = ["gf", "f1", "f2"][:num_floors]
    floor_areas  = {"gf": project.get("gf_area", 0.0), "f1": project.get("f1_area", 0.0), "f2": project.get("f2_area", 0.0)}
    floor_heights= {"gf": project.get("gf_height", 4.0), "f1": project.get("f1_height", 4.0), "f2": project.get("f2_height", 4.0)}

    floors_data = {}
    total_balcony = 0.0

    for fk in floor_keys:
        fdata = _render_floor_inputs(fk, float(floor_areas.get(fk, 0.0)), float(floor_heights.get(fk, 4.0)))
        floors_data[fk] = fdata
        total_balcony += fdata.get("balcony_area", 0.0)
        st.divider()

    # Store balcony area for BOQ
    floors_data["balcony_area"] = total_balcony

    # ── Live Results Preview ──
    st.markdown("#### Live Results Preview | نتائج مباشرة")
    results = calc_villa_finishes(
        floors_data,
        num_floors,
        project.get("ext_perimeter", 0.0),
        project.get("total_height", 0.0),
        project.get("roof_area", 0.0),
        total_balcony,
    )

    for fk in floor_keys:
        fres = results.get(fk, {})
        label = _FLOOR_LABELS.get(fk, fk)
        st.markdown(f"**{label}**")
        preview_rows = [{"Item": en, "البيان": ar, "Unit": unit, "Quantity": round(fres.get(key, 0.0), 2)}
                        for key, en, ar, unit in _FINISH_KEYS]
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    st.markdown("**Villa-Wide | الفيلا كاملة**")
    villa_wide = [
        ("External Plaster",       "لياسة خارجية",       "m²", results.get("external_plaster", 0)),
        ("External Finishes",      "تشطيب خارجي",        "m²", results.get("external_finishes", 0)),
        ("Wet Waterproofing",      "عزل مناطق رطبة",     "m²", results.get("wet_waterproofing", 0)),
        ("Roof Waterproofing",     "عزل السطح",           "m²", results.get("roof_waterproofing", 0)),
    ]
    st.dataframe(
        pd.DataFrame([{"Item": en, "البيان": ar, "Unit": unit, "Quantity": round(float(qty), 2)}
                      for en, ar, unit, qty in villa_wide]),
        use_container_width=True, hide_index=True,
    )

    return floors_data
