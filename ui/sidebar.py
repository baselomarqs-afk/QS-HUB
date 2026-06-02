import streamlit as st
from utils.i18n import t

def render_sidebar() -> dict:
    """Renders all global project inputs and returns them as a dict"""
    st.sidebar.title(t("sidebar_title"))
    st.sidebar.markdown("---")

    project_name = st.sidebar.text_input(t("project_name"), value=st.session_state.get("project_name", "Villa Project"))
    st.session_state["project_name"] = project_name

    num_floors = st.sidebar.selectbox(
        t("num_floors"),
        options=[1, 2, 3],
        format_func=lambda x: {1: "G+1", 2: "G+2", 3: "G+3"}[x],
        index=st.session_state.get("num_floors_idx", 1),
    )
    st.session_state["num_floors_idx"] = [1,2,3].index(num_floors)

    st.sidebar.markdown(t("sidebar_areas"))
    gf_area   = st.sidebar.number_input(t("gf_area"),   min_value=0.0, value=float(st.session_state.get("gf_area", 0.0)),   step=1.0)
    f1_area   = st.sidebar.number_input(t("f1_area"),    min_value=0.0, value=float(st.session_state.get("f1_area", 0.0)),   step=1.0) if num_floors >= 2 else 0.0
    f2_area   = st.sidebar.number_input(t("f2_area"),   min_value=0.0, value=float(st.session_state.get("f2_area", 0.0)),   step=1.0) if num_floors >= 3 else 0.0
    roof_area = st.sidebar.number_input(t("roof_area"),  min_value=0.0, value=float(st.session_state.get("roof_area", 0.0)), step=1.0)
    plot_area = st.sidebar.number_input(t("plot_area"), min_value=0.0, value=float(st.session_state.get("plot_area", 0.0)), step=1.0)

    st.sidebar.markdown(t("sidebar_dims"))
    ext_perimeter = st.sidebar.number_input(t("ext_perimeter"), min_value=0.0, value=float(st.session_state.get("ext_perimeter", 0.0)), step=0.5)
    longest_length= st.sidebar.number_input(t("longest_length"),           min_value=0.0, value=float(st.session_state.get("longest_length", 0.0)), step=0.5)
    longest_width = st.sidebar.number_input(t("longest_width"),            min_value=0.0, value=float(st.session_state.get("longest_width", 0.0)),  step=0.5)
    roof_perimeter= st.sidebar.number_input(t("roof_perimeter"),         min_value=0.0, value=float(st.session_state.get("roof_perimeter", 0.0)), step=0.5)
    compound_len  = st.sidebar.number_input(t("compound_len"),    min_value=0.0, value=float(st.session_state.get("compound_len", 0.0)),   step=0.5)

    st.sidebar.markdown(t("sidebar_heights"))
    gf_height  = st.sidebar.number_input(t("gf_height"), min_value=0.0, value=float(st.session_state.get("gf_height", 4.0)), step=0.1)
    f1_height  = st.sidebar.number_input(t("f1_height"), min_value=0.0, value=float(st.session_state.get("f1_height", 4.0)), step=0.1) if num_floors >= 2 else 0.0
    f2_height  = st.sidebar.number_input(t("f2_height"), min_value=0.0, value=float(st.session_state.get("f2_height", 4.0)), step=0.1) if num_floors >= 3 else 0.0
    total_height = gf_height + f1_height + f2_height

    # Save all to session state
    for k, v in {
        "project_name": project_name, "num_floors": num_floors,
        "gf_area": gf_area, "f1_area": f1_area, "f2_area": f2_area,
        "roof_area": roof_area, "plot_area": plot_area,
        "ext_perimeter": ext_perimeter, "longest_length": longest_length,
        "longest_width": longest_width, "roof_perimeter": roof_perimeter,
        "compound_len": compound_len,
        "gf_height": gf_height, "f1_height": f1_height, "f2_height": f2_height,
        "total_height": total_height,
    }.items():
        st.session_state[k] = v

    return {
        "project_name": project_name, "num_floors": num_floors,
        "gf_area": gf_area, "f1_area": f1_area, "f2_area": f2_area,
        "roof_area": roof_area, "plot_area": plot_area,
        "ext_perimeter": ext_perimeter, "longest_length": longest_length,
        "longest_width": longest_width, "roof_perimeter": roof_perimeter,
        "compound_len": compound_len, "total_height": total_height,
        "gf_height": gf_height, "f1_height": f1_height, "f2_height": f2_height,
    }
