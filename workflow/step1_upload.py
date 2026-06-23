"""
STEP 1 — Upload Drawings
"""
from pdf_engine.pdf_loader import load_pdf_pages, extract_page_text
from workflow.workflow_state import mark_step_done
from utils.i18n import t
from utils.storage import save_file
from utils.usage import check_file_size

def render_step1() -> bool:
    import streamlit as st
    st.markdown(t("upload_title"))
    st.caption(t("upload_caption"))

    # Check project limit BEFORE allowing upload
    user = st.session_state.get("user")
    from utils.usage import EVENT_PROJECT, check_limit
    ok, msg = check_limit(user, EVENT_PROJECT) if user else (True, "OK")
    if not ok:
        st.error(f"🚨 {msg}")
        st.warning("You cannot start a new project because your monthly limit is exhausted.")
        st.markdown("### How to proceed?")
        c1, c2 = st.columns(2)
        with c1:
            st.info("💡 **Option 1:** Buy a single extra project allowance that never expires.")
            if st.button("🛒 Buy +1 Project (50 AED)", type="primary", use_container_width=True):
                try:
                    from utils.payments import create_addon_checkout_session
                    checkout_url = create_addon_checkout_session(user)
                    st.link_button("Proceed to Secure Payment", checkout_url, use_container_width=True)
                except Exception:
                    st.warning("⚠️ **Payment Gateway (Paddle) is not configured yet.**\n\n*Preview Mode:* In the final version, this button will securely redirect the user to Paddle to pay 50 AED, and then immediately unlock their account.")
        with c2:
            st.info("🚀 **Option 2:** Upgrade your monthly plan for higher limits.")
            if st.button("⬆️ View Plans & Upgrade", use_container_width=True):
                st.query_params["page"] = "billing"
                st.rerun()
        return False

    st.markdown("### Project Details | تفاصيل المشروع")
    project_name = st.text_input(
        "Project Name (Optional) | اسم المشروع (اختياري)",
        value=st.session_state.get("project_name", ""),
        help="Give your project a unique name to find it easily later in the Projects page."
    )
    if project_name.strip():
        st.session_state["project_name"] = project_name.strip()

    st.write("")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(t("upload_str_title"))
        str_file = st.file_uploader(
            t("upload_str_hint"),
            type=["pdf"], key="up_str"
        )

    with col2:
        st.markdown(t("upload_arch_title"))
        arch_file = st.file_uploader(
            t("upload_arch_hint"),
            type=["pdf"], key="up_arch"
        )

    if str_file:
        if st.session_state.get("str_fname") != str_file.name:
            from workflow.workflow_state import reset_pipeline
            reset_pipeline()
            with st.spinner(t("upload_processing_str")):
                b = str_file.read()
                user = st.session_state.get("user", {})
                ok, msg = check_file_size(user, len(b)) if user else (True, "OK")
                if not ok:
                    st.error(msg)
                    return False
                if user:
                    save_file(user["id"], str_file.name, b, "application/pdf")
                st.session_state["str_pages"]  = load_pdf_pages(b)
                st.session_state["str_texts"]  = extract_page_text(b)
                st.session_state["str_fname"]  = str_file.name
            st.success(f"{t('upload_success_str')}: {len(st.session_state['str_pages'])} {t('upload_pages')}")

    if arch_file:
        if st.session_state.get("arch_fname") != arch_file.name:
            from workflow.workflow_state import reset_pipeline
            reset_pipeline()
            with st.spinner(t("upload_processing_arch")):
                b = arch_file.read()
                user = st.session_state.get("user", {})
                ok, msg = check_file_size(user, len(b)) if user else (True, "OK")
                if not ok:
                    st.error(msg)
                    return False
                if user:
                    save_file(user["id"], arch_file.name, b, "application/pdf")
                st.session_state["arch_pages"] = load_pdf_pages(b)
                st.session_state["arch_texts"] = extract_page_text(b)
                st.session_state["arch_fname"] = arch_file.name
            st.success(f"{t('upload_success_arch')}: {len(st.session_state['arch_pages'])} {t('upload_pages')}")

    has_any = (
        len(st.session_state.get("str_pages", [])) > 0 or
        len(st.session_state.get("arch_pages", [])) > 0
    )

    if has_any:
        total = (
            len(st.session_state.get("str_pages", [])) +
            len(st.session_state.get("arch_pages", []))
        )
        st.info(f"{t('upload_total')} **{total}**")

        if st.button(t("upload_next_btn"), type="primary", use_container_width=True):
            mark_step_done("upload")
            return True

    return False
