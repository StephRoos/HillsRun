"""Sync Management page."""

import time

import pandas as pd
import streamlit as st

import api_client

st.set_page_config(page_title="Sync Management", page_icon="🔄", layout="wide")
st.title("Sync Management")

ALL_CATEGORIES = [
    "daily_health",
    "activities",
    "body_composition",
    "advanced_metrics",
    "wellness",
]

# ── Section 1: Current sync status ──────────────────────────────────────────

st.header("Current Status")

try:
    status_data = api_client.get_sync_status()
    if status_data:
        cols = st.columns(len(status_data))
        for col, cat in zip(cols, status_data):
            with col:
                category = cat.get("category", "?")
                sync_status = cat.get("sync_status", "unknown")
                last_date = cat.get("last_sync_date", "never")
                records = cat.get("records_synced", 0)

                status_color = "🟢" if sync_status == "success" else "🔴" if sync_status == "failed" else "🟡"
                st.metric(
                    label=f"{status_color} {category}",
                    value=f"{records or 0} records",
                    delta=f"Last: {last_date}" if last_date else "Never synced",
                )
    else:
        st.info("No sync data yet. Run a sync to get started.")
except Exception as e:
    st.error(f"Failed to load sync status: {e}")

st.divider()

# ── Section 2: Trigger a sync ────────────────────────────────────────────────

st.header("Launch Sync")

with st.form("sync_form"):
    col1, col2 = st.columns(2)

    with col1:
        selected_categories = st.multiselect(
            "Categories",
            options=ALL_CATEGORIES,
            default=ALL_CATEGORIES,
        )
        mode = st.selectbox("Mode", ["incremental", "full"])
        days_back = st.number_input("Days back (full mode)", min_value=1, max_value=365, value=90)

    with col2:
        use_date_range = st.checkbox("Use custom date range")
        start_date = st.date_input("Start date") if use_date_range else None
        end_date = st.date_input("End date") if use_date_range else None
        dry_run = st.checkbox("Dry run (preview only)")

    submitted = st.form_submit_button("Start Sync", type="primary")

if submitted:
    try:
        result = api_client.trigger_sync(
            categories=selected_categories or None,
            mode=mode,
            days_back=days_back,
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
            dry_run=dry_run,
        )
        st.session_state["active_job_id"] = result["job_id"]
        st.success(f"Sync started — Job ID: `{result['job_id']}`")
    except Exception as e:
        st.error(f"Failed to trigger sync: {e}")

st.divider()

# ── Section 3: Active job progress ──────────────────────────────────────────

st.header("Job Progress")

active_job_id = st.session_state.get("active_job_id")

if active_job_id:
    progress_placeholder = st.empty()
    log_placeholder = st.empty()

    # Poll loop
    for _ in range(120):  # max ~2 min of polling
        try:
            job = api_client.get_job(active_job_id)
        except Exception as e:
            st.error(f"Error polling job: {e}")
            break

        status = job.get("status", "unknown")

        with progress_placeholder.container():
            if status == "running":
                st.info(f"Status: **{status}** — started at {job.get('started_at', '?')}")
            elif status == "completed":
                st.success(f"Sync completed at {job.get('finished_at', '?')}")
            elif status == "failed":
                st.error(f"Sync failed: {job.get('error', 'unknown error')}")
            else:
                st.warning(f"Status: {status}")

        with log_placeholder.container():
            logs = job.get("logs", [])
            if logs:
                st.text_area("Logs", value="\n".join(logs[-50:]), height=300, disabled=True)

        if status in ("completed", "failed"):
            if status == "completed" and job.get("result"):
                st.json(job["result"])
            st.session_state.pop("active_job_id", None)
            break

        time.sleep(1)
        st.rerun()
else:
    st.info("No active sync job. Trigger a sync above or select a job from history.")

st.divider()

# ── Section 4: Job history ──────────────────────────────────────────────────

st.header("History")

try:
    jobs = api_client.list_jobs(limit=10)
    if jobs:
        rows = []
        for j in jobs:
            rows.append({
                "Job ID": j["job_id"][:8] + "...",
                "Status": j["status"],
                "Mode": j["request"]["mode"],
                "Dry Run": j["request"].get("dry_run", False),
                "Created": j.get("created_at", ""),
                "Finished": j.get("finished_at", ""),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Allow selecting a job to view details
        job_ids = [j["job_id"] for j in jobs]
        selected = st.selectbox("View job details", [""] + job_ids, format_func=lambda x: x[:8] + "..." if x else "Select a job")
        if selected:
            job_detail = api_client.get_job(selected)
            st.json(job_detail)
    else:
        st.info("No sync jobs yet.")
except Exception as e:
    st.error(f"Failed to load job history: {e}")
