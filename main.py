import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from database import (
    get_activity_stats,
    get_all_activities,
    get_latest_activity_date,
    init_db,
    save_activities,
)
from garmin_client import GarminClient

load_dotenv()
init_db()

st.set_page_config(page_title="HillsRun", page_icon="🏃", layout="wide")
st.title("HillsRun")

# --- Sidebar ---
with st.sidebar:
    st.header("Synchronisation")

    email = os.getenv("GARMIN_EMAIL", "")
    password = os.getenv("GARMIN_PASSWORD", "")

    if not email or not password:
        st.warning("Configure GARMIN_EMAIL et GARMIN_PASSWORD dans .env")

    sync_mode = st.radio(
        "Mode de synchronisation",
        ["Incrémentale", "Complète"],
        index=0,
    )

    def _sync_activities(garmin_client: GarminClient):
        with st.spinner("Récupération des activités..."):
            if sync_mode == "Incrémentale":
                latest = get_latest_activity_date()
                if latest:
                    st.info(f"Synchro depuis {latest}")
                    acts = garmin_client.get_activities_since(latest)
                else:
                    st.info("Première synchro — import complet")
                    acts = garmin_client.get_all_activities()
            else:
                acts = garmin_client.get_all_activities()

            save_activities(acts)
            st.success(f"{len(acts)} activités synchronisées")
            st.session_state.pop("mfa_needed", None)
            st.session_state.pop("garmin_client", None)

    # MFA flow
    if st.session_state.get("mfa_needed"):
        mfa_code = st.text_input("Code MFA", placeholder="123456")
        if st.button("Valider MFA"):
            try:
                garmin = st.session_state["garmin_client"]
                garmin.resume_mfa(mfa_code)
                _sync_activities(garmin)
            except Exception as e:
                st.error(f"Erreur MFA : {e}")
                st.session_state.pop("mfa_needed", None)

    elif st.button("Synchroniser", disabled=not email or not password):
        with st.spinner("Connexion à Garmin Connect..."):
            try:
                garmin = GarminClient(email, password)
                needs_mfa = garmin.login()

                if needs_mfa:
                    st.session_state["mfa_needed"] = True
                    st.session_state["garmin_client"] = garmin
                    st.warning("Code MFA requis — vérifiez votre appareil")
                    st.rerun()
                else:
                    _sync_activities(garmin)
            except Exception as e:
                st.error(f"Erreur : {e}")

    latest_date = get_latest_activity_date()
    if latest_date:
        st.caption(f"Dernière activité : {latest_date}")

# --- Main content ---
activities = get_all_activities()

if not activities:
    st.info("Aucune activité. Lancez une synchronisation depuis la sidebar.")
    st.stop()

df = pd.DataFrame(activities)

# KPIs
stats = get_activity_stats()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Activités", stats["total_activities"])
col2.metric("Distance totale", f"{stats['total_distance'] / 1000:.1f} km")
col3.metric("Durée totale", f"{stats['total_duration'] / 3600:.1f} h")
col4.metric("FC moyenne", f"{stats['avg_hr']:.0f} bpm")

st.divider()

# Activity table
st.subheader("Activités")

df_display = df.copy()
df_display["distance_km"] = df_display["distance"].apply(
    lambda x: f"{x / 1000:.2f}" if x else "—"
)
df_display["duration_min"] = df_display["duration"].apply(
    lambda x: f"{x / 60:.1f}" if x else "—"
)
df_display["allure"] = df_display.apply(
    lambda row: (
        f"{row['duration'] / 60 / (row['distance'] / 1000):.2f}"
        if row.get("distance") and row["distance"] > 0 and row.get("duration")
        else "—"
    ),
    axis=1,
)

st.dataframe(
    df_display[
        [
            "activity_name",
            "activity_type",
            "start_time",
            "distance_km",
            "duration_min",
            "allure",
            "average_hr",
            "elevation_gain",
        ]
    ].rename(
        columns={
            "activity_name": "Nom",
            "activity_type": "Type",
            "start_time": "Date",
            "distance_km": "Distance (km)",
            "duration_min": "Durée (min)",
            "allure": "Allure (min/km)",
            "average_hr": "FC moy.",
            "elevation_gain": "D+ (m)",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.divider()

# Charts
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Distance par activité")
    df_chart = df[df["distance"].notna()].copy()
    df_chart["start_time"] = pd.to_datetime(df_chart["start_time"])
    df_chart["distance_km"] = df_chart["distance"] / 1000
    df_chart = df_chart.sort_values("start_time")
    fig = px.line(
        df_chart,
        x="start_time",
        y="distance_km",
        labels={"start_time": "Date", "distance_km": "Distance (km)"},
        markers=True,
    )
    st.plotly_chart(fig, width="stretch")

with col_right:
    st.subheader("Répartition par type")
    type_counts = df["activity_type"].value_counts().reset_index()
    type_counts.columns = ["Type", "Nombre"]
    fig = px.pie(type_counts, names="Type", values="Nombre")
    st.plotly_chart(fig, width="stretch")

st.divider()

# Monthly summary
st.subheader("Résumé mensuel")
df_monthly = df.copy()
df_monthly["start_time"] = pd.to_datetime(df_monthly["start_time"])
df_monthly["mois"] = df_monthly["start_time"].dt.to_period("M").astype(str)

monthly = (
    df_monthly.groupby("mois")
    .agg(
        activités=("activity_id", "count"),
        distance_km=("distance", lambda x: x.sum() / 1000),
        durée_h=("duration", lambda x: x.sum() / 3600),
        fc_moyenne=("average_hr", "mean"),
        d_pos=("elevation_gain", "sum"),
    )
    .sort_index(ascending=False)
    .reset_index()
)

monthly.columns = ["Mois", "Activités", "Distance (km)", "Durée (h)", "FC moy.", "D+ (m)"]
monthly["Distance (km)"] = monthly["Distance (km)"].apply(lambda x: f"{x:.1f}")
monthly["Durée (h)"] = monthly["Durée (h)"].apply(lambda x: f"{x:.1f}")
monthly["FC moy."] = monthly["FC moy."].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
monthly["D+ (m)"] = monthly["D+ (m)"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "—")

st.dataframe(monthly, width="stretch", hide_index=True)
