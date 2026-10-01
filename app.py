import streamlit as st

st.set_page_config(page_title="Stock AI Pro", page_icon="📈", layout="wide")

from config.runtime import runtime_info, validate_runtime
from ui.dashboard import render_dashboard

problems = validate_runtime()
if problems:
    st.error("\n".join(problems))
    st.stop()

with st.sidebar.expander("🧩 실행환경", expanded=False):
    st.json(runtime_info())

render_dashboard()
