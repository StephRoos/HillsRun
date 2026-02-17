"""HillsRun Dashboard — entry point."""

import streamlit as st

st.set_page_config(
    page_title="HillsRun Dashboard",
    page_icon="🏔️",
    layout="wide",
)

st.title("HillsRun Dashboard")

# Sidebar
st.sidebar.title("Navigation")
st.sidebar.info("Use the pages in the sidebar to navigate.")

# Home page content
st.markdown(
    """
    Welcome to the **HillsRun** dashboard.

    ### Available pages
    - **Sync Management** — Monitor and trigger Garmin data synchronisation

    ### Quick status
    """
)

# Show API connectivity
try:
    from api_client import health_check

    status = health_check()
    st.success(f"API connected — status: {status.get('status', 'ok')}")
except Exception as e:
    st.error(f"API unreachable: {e}")
