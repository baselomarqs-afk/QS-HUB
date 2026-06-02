import pathlib

import streamlit as st

from utils.i18n import get_lang


ROOT = pathlib.Path(__file__).resolve().parent.parent
LEGAL_DIR = ROOT / "legal"


DOCS = [
    ("Terms", "TERMS_OF_USE"),
    ("Privacy", "PRIVACY_POLICY"),
    ("Refund", "REFUND_POLICY"),
    ("Data Retention", "DATA_RETENTION"),
    ("Engineering Disclaimer", "ENGINEERING_DISCLAIMER"),
]


def _read_doc(base_name: str) -> str:
    suffix = "AR" if get_lang() == "ar" else "EN"
    path = LEGAL_DIR / f"{base_name}_{suffix}.md"
    if not path.exists():
        return "Document not found."
    return path.read_text(encoding="utf-8")


def render_legal():
    st.markdown("<h1 style='color:#3b82f6;'>Legal & Compliance</h1>", unsafe_allow_html=True)
    st.caption("Terms, privacy, refunds, data retention, and engineering disclaimer.")
    st.divider()

    tabs = st.tabs([label for label, _ in DOCS])
    for tab, (_, base_name) in zip(tabs, DOCS):
        with tab:
            st.markdown(_read_doc(base_name))
