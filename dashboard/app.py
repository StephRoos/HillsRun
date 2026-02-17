"""HillsRun Dashboard — entry point."""

from datetime import date, timedelta

import streamlit as st

st.set_page_config(
    page_title="HillsRun Dashboard",
    page_icon="\U0001f3d4\ufe0f",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.title("HillsRun")

# Date picker (used by Home page)
selected_date = st.sidebar.date_input(
    "Date",
    value=date.today(),
    max_value=date.today(),
    min_value=date.today() - timedelta(days=365),
)

st.sidebar.divider()

# API status
try:
    from api_client import health_check

    status = health_check()
    st.sidebar.success(f"API: {status.get('status', 'ok')}")
except Exception:
    st.sidebar.error("API unreachable")

# ── Page router ────────────────────────────────────────────────────────────
# Streamlit's native multi-page app uses the pages/ directory automatically.
# We render the Home page content here (the main app.py IS the home page).

from home import render as render_home  # noqa: E402

render_home(selected_date=selected_date)
