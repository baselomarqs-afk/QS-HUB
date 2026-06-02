import streamlit as st
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from utils.i18n import get_lang

st.set_page_config(page_title="Terms of Service", page_icon="📜")
st.page_link("app.py", label="← Back to App Home", icon="🏠")
st.divider()

suffix = "AR" if get_lang() == "ar" else "EN"
path = ROOT / "legal" / f"TERMS_OF_USE_{suffix}.md"
if path.exists():
    st.markdown(path.read_text(encoding="utf-8"))
else:
    st.error("Terms of Service document not found.")
