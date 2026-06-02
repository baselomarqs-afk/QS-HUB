"""
تبويب رفع PDFs مع معاينة بصرية وتصنيف يدوي — مستوحى من simple app
"""
import streamlit as st

from pdf_engine.pdf_loader       import load_pdf_pages, extract_page_text, page_to_pil
from pdf_engine.smart_classifier import classify_all_pages, PAGE_ITEMS_MAP
from pdf_engine.scale_detector   import calculate_ppm, manual_scale_override

# ── Drawing type display labels (mirrors the simple app sidebar) ──────────────
_STRUCTURAL = [
    ("foundations",   "️ Foundations | أساسات"),
    ("tie_beam",      "━  Tie Beam | الميدة"),
    ("upper_columns", " Columns Schedule | الأعمدة"),
    ("slab_1st",      "⬛ 1st Floor Slab | بلاطة الأول"),
    ("slab_2nd",      "⬛ 2nd Floor Slab | بلاطة الثاني"),
    ("roof_slab",     " Roof Slab | بلاطة السطح"),
]

_ARCH = [
    ("setting_out",       " Setting Out Plan | الموقع"),
    ("ground_floor_plan", " Ground Floor Plan | الأرضي"),
    ("first_floor_plan",  "1️⃣ 1st Floor Plan | الأول"),
    ("second_floor_plan", "2️⃣ 2nd Floor Plan | الثاني"),
    ("roof_floor_plan",   " Roof Floor Plan | السطح"),
    ("elevations",        "️ Elevations | الواجهات"),
    ("schedules",         " Schedules | الجداول"),
]

_ALL_OPTIONS = ["unknown"] + [k for k, _ in _STRUCTURAL + _ARCH]

_LABELS: dict = {"unknown": "❓ Not assigned | غير محدد"}
_LABELS.update({k: lbl for k, lbl in _STRUCTURAL + _ARCH})

_CONF_ICON = {"high": "", "medium": "", "low": "", "manual": ""}


def render_pdf_tab() -> dict:
    st.header(" PDF Upload & Page Mapping | رفع المخططات وتصنيف الصفحات")
    st.caption(
        "**Step 1:** Upload Structural & Architectural PDFs  →  "
        "**Step 2:** Assign each page its drawing type  →  "
        "**Step 3:** Confirm → AI Vision"
    )

    # ── STEP 1 — Upload ───────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ️ Structural | الإنشائي")
        str_pdf = st.file_uploader(
            "Structural PDF",
            type=["pdf"],
            key="str_pdf_uploader",
            help="Foundation, columns, beams, slabs drawings",
        )
    with col2:
        st.markdown("####  Architectural | المعماري")
        arch_pdf = st.file_uploader(
            "Architectural PDF",
            type=["pdf"],
            key="arch_pdf_uploader",
            help="Floor plans, elevations, door/window schedules",
        )

    all_pages_images = st.session_state.get("all_pages_images", {})
    changed = False

    if str_pdf:
        raw = str_pdf.read()
        if st.session_state.get("str_pdf_name") != str_pdf.name:
            with st.spinner("Loading structural pages..."):
                pages      = load_pdf_pages(raw, dpi=150)
                texts      = extract_page_text(raw)
                classified = classify_all_pages(texts, pdf_name="structural")
                st.session_state["str_pages"]      = pages
                st.session_state["str_classified"]  = classified
                st.session_state["str_pdf_name"]   = str_pdf.name
                st.session_state["str_page_texts"] = texts
                all_pages_images["structural"]     = pages
            st.success(f" Structural: {len(pages)} pages loaded")
            changed = True

    if arch_pdf:
        raw = arch_pdf.read()
        if st.session_state.get("arch_pdf_name") != arch_pdf.name:
            with st.spinner("Loading architectural pages..."):
                pages      = load_pdf_pages(raw, dpi=150)
                texts      = extract_page_text(raw)
                classified = classify_all_pages(texts, pdf_name="architectural")
                st.session_state["arch_pages"]     = pages
                st.session_state["arch_classified"] = classified
                st.session_state["arch_pdf_name"]  = arch_pdf.name
                st.session_state["arch_page_texts"] = texts
                all_pages_images["architectural"]  = pages
            st.success(f" Architectural: {len(pages)} pages loaded")
            changed = True

    if changed:
        combined = (
            st.session_state.get("str_classified", []) +
            st.session_state.get("arch_classified", [])
        )
        st.session_state["all_classified_pages"] = combined
        st.session_state["all_pages_images"]     = all_pages_images
        # backward compat for OCR / detection tabs
        st.session_state["pdf_pages"] = (
            st.session_state.get("str_pages", []) +
            st.session_state.get("arch_pages", [])
        )

    all_classified = st.session_state.get("all_classified_pages", [])
    if not all_classified:
        st.info(" Upload at least one PDF above to begin.")
        return {}

    # ── STEP 2 — Visual Page Grid + Assignment ────────────────────────────────
    st.markdown("---")

    # Legend
    with st.expander(" Drawing Type Legend | أنواع الرسومات", expanded=False):
        lc, rc = st.columns(2)
        with lc:
            st.markdown("**️ Structural**")
            for _, lbl in _STRUCTURAL:
                st.caption(f"• {lbl}")
        with rc:
            st.markdown("** Architectural**")
            for _, lbl in _ARCH:
                st.caption(f"• {lbl}")

    st.markdown("####  Assign Drawing Types | حدد نوع كل صفحة")
    st.caption(
        "Each page is shown below. The system auto-detects the type ( high /  medium /  low confidence). "
        "Change any assignment using the dropdown."
    )

    # Build list of (page_info, image_array)
    pages_with_imgs = []
    for p in all_classified:
        src_imgs = all_pages_images.get(p["pdf_name"], [])
        if p["page_index"] < len(src_imgs):
            pages_with_imgs.append((p, src_imgs[p["page_index"]]))

    # Render 3-column grid
    COLS = 3
    for row_start in range(0, len(pages_with_imgs), COLS):
        row_items = pages_with_imgs[row_start: row_start + COLS]
        cols = st.columns(COLS)
        for col, (pinfo, img_arr) in zip(cols, row_items):
            with col:
                pil = page_to_pil(img_arr)
                auto_type = pinfo["detected_type"]
                conf_icon = _CONF_ICON.get(pinfo["confidence"], "⚪")

                st.image(
                    pil,
                    use_container_width=True,
                    caption=f"{pinfo['pdf_name'].title()} · Page {pinfo['page_number']}",
                )

                # Current auto-detected badge
                st.markdown(
                    f"<div style='font-size:11px; color:#888;'>"
                    f"{conf_icon} auto: <b>{auto_type.replace('_',' ').title()}</b>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Assignment selectbox — Streamlit stores value in session_state[key]
                sel_key = f"page_type_{pinfo['pdf_name']}_{pinfo['page_index']}"
                default_idx = (
                    _ALL_OPTIONS.index(auto_type)
                    if auto_type in _ALL_OPTIONS else 0
                )
                st.selectbox(
                    "Type",
                    options=_ALL_OPTIONS,
                    index=default_idx,
                    format_func=lambda k: _LABELS.get(k, k),
                    key=sel_key,
                    label_visibility="collapsed",
                )

    # ── STEP 2b — Scale ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("####  Drawing Scale | مقياس الرسم")
    
    # Read query parameter ppm if it exists from interactive canvas click
    if "ppm" in st.query_params:
        try:
            url_ppm = float(st.query_params["ppm"])
            st.session_state["pixels_per_meter"] = url_ppm
            st.query_params.clear()
            st.success(f"✅ Calibrated via Interactive Canvas: {url_ppm:.1f} px/m")
        except Exception:
            pass

    sc1, sc2 = st.columns(2)
    with sc1:
        scale_text = st.text_input("Scale ratio (e.g. 1:100)", value="1:100", key="scale_input")
        ppm = calculate_ppm(scale_text)
        if ppm and "pixels_per_meter" not in st.session_state:
            st.session_state["pixels_per_meter"] = ppm
            st.success(f" {ppm:.1f} px/m")
    with sc2:
        st.caption("Or calculate from a known distance:")
        kp = st.number_input("Known distance in pixels", min_value=0.0, value=0.0, step=1.0, key="kp_input")
        km = st.number_input("Known distance in meters",  min_value=0.0, value=0.0, step=0.5, key="km_input")
        if kp > 0 and km > 0:
            ppm2 = manual_scale_override(kp, km)
            st.success(f" {ppm2:.1f} px/m")
            st.session_state["pixels_per_meter"] = ppm2

    st.write(f"**Current Scale: {st.session_state.get('pixels_per_meter', 0.0):.1f} pixels per meter**")

    # Render Interactive HTML5 Canvas Scale Tool if page images are loaded
    if pages_with_imgs:
        st.markdown("##### 📏 Interactive Calibration Canvas | لوحة الرسم التفاعلية للمعايرة")
        selected_page_idx = st.selectbox(
            "Select Page for Calibration | اختر الصفحة للمعايرة",
            range(len(pages_with_imgs)),
            format_func=lambda i: f"{pages_with_imgs[i][0]['pdf_name'].title()} · Page {pages_with_imgs[i][0]['page_number']}"
        )
        
        from utils.canvas_component import render_interactive_canvas
        cal_pinfo, cal_img = pages_with_imgs[selected_page_idx]
        
        # Display the custom interactive canvas
        render_interactive_canvas(cal_img, width=800, height=600)

    # ── STEP 3 — Confirm ──────────────────────────────────────────────────────
    st.markdown("---")

    n_assigned = sum(
        1 for p in all_classified
        if st.session_state.get(
            f"page_type_{p['pdf_name']}_{p['page_index']}",
            p["detected_type"]
        ) != "unknown"
    )

    if st.button(
        f" Confirm Mapping — {n_assigned} pages assigned | تأكيد التصنيف",
        type="primary",
        key="btn_confirm_pages",
    ):
        # Collect current selectbox values and rebuild all_classified_pages
        finalised = []
        for p in all_classified:
            sel_key  = f"page_type_{p['pdf_name']}_{p['page_index']}"
            selected = st.session_state.get(sel_key, p["detected_type"])
            finalised.append({
                **p,
                "detected_type": selected,
                "extract_items": PAGE_ITEMS_MAP.get(selected, {}).get("extract_items", []),
                "ai_focus":      PAGE_ITEMS_MAP.get(selected, {}).get("ai_prompt_focus", ""),
                "confidence":    "manual" if selected != p["detected_type"] else p["confidence"],
            })
        st.session_state["all_classified_pages"] = finalised
        st.session_state["pdf_ready"]            = True
        st.success(f" {n_assigned} pages confirmed! Go to AI Vision tab.")

    # Summary table after confirmation
    if st.session_state.get("pdf_ready"):
        done = [
            p for p in st.session_state["all_classified_pages"]
            if p["detected_type"] != "unknown"
        ]
        st.info(
            f" **{len(done)} pages ready** — "
            + ", ".join(
                f"{p['pdf_name'].title()} P{p['page_number']}→{p['detected_type'].replace('_',' ')}"
                for p in done
            )
        )

    return {
        "classified_pages": st.session_state.get("all_classified_pages", []),
        "ready":            st.session_state.get("pdf_ready", False),
        "ppm":              st.session_state.get("pixels_per_meter", 0.0),
    }
