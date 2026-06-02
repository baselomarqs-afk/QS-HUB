import streamlit as st
import pandas as pd
from engine.openings import calc_doors, calc_windows


_DEFAULT_DOORS = [
    {"type": "Main Entrance", "count": 1},
    {"type": "Room Door",     "count": 4},
    {"type": "Bathroom Door", "count": 3},
]

_DEFAULT_WINDOWS = [
    {"type": "Living Room Window", "length": 2.0, "width": 1.5, "count": 2},
    {"type": "Bedroom Window",     "length": 1.2, "width": 1.2, "count": 4},
]


def _init_state():
    if "open_doors" not in st.session_state:
        st.session_state["open_doors"] = pd.DataFrame(_DEFAULT_DOORS)
    if "open_windows" not in st.session_state:
        st.session_state["open_windows"] = pd.DataFrame(_DEFAULT_WINDOWS)


def render_openings_tab() -> dict:
    _init_state()

    st.subheader(" Openings | الفتحات")

    # ── Doors ──
    st.markdown("#### Doors | الأبواب")
    doors_df = st.data_editor(
        st.session_state["open_doors"],
        num_rows="dynamic",
        use_container_width=True,
        key="de_doors",
        column_config={
            "type":  st.column_config.TextColumn("Door Type | نوع الباب", width="large"),
            "count": st.column_config.NumberColumn("Count | العدد", min_value=0, step=1, format="%d"),
        },
    )
    st.session_state["open_doors"] = doors_df

    doors_list = doors_df.to_dict("records") if not doors_df.empty else []
    total_doors = calc_doors(doors_list)
    st.metric("Total Doors | إجمالي الأبواب", f"{int(total_doors)} Nr")

    st.divider()

    # ── Windows ──
    st.markdown("#### Windows | النوافذ")
    windows_df = st.data_editor(
        st.session_state["open_windows"],
        num_rows="dynamic",
        use_container_width=True,
        key="de_windows",
        column_config={
            "type":   st.column_config.TextColumn("Window Type | نوع النافذة", width="medium"),
            "length": st.column_config.NumberColumn("Length (m)", min_value=0.0, step=0.1, format="%.2f"),
            "width":  st.column_config.NumberColumn("Width (m)",  min_value=0.0, step=0.1, format="%.2f"),
            "count":  st.column_config.NumberColumn("Count | العدد", min_value=0, step=1, format="%d"),
        },
    )
    st.session_state["open_windows"] = windows_df

    windows_list = windows_df.to_dict("records") if not windows_df.empty else []
    total_windows = calc_windows(windows_list)
    st.metric("Total Window Area | إجمالي مساحة النوافذ", f"{total_windows:.2f} m²")

    return {
        "doors":   doors_list,
        "windows": windows_list,
    }
