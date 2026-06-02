import streamlit as st
from ui.page_billing import render_billing
from utils.i18n import get_lang, set_lang
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

st.set_page_config(page_title="Pricing & Billing", page_icon="💳")

st.page_link("app.py", label="← Back to App Home", icon="🏠")
st.write("")

# Force language from URL or session if needed
if "user" not in st.session_state:
    st.session_state["user"] = None

render_billing()
