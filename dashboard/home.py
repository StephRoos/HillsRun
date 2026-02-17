"""Home page — athlete summary with KPIs, fitness status, and recent activities."""

from datetime import date, datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

import api_client
from utils import (
    format_duration,
    sport_icon,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_get(fn, **kwargs):
    """Call an API function and return its result, or empty list on error."""
    try:
        return fn(**kwargs)
    except Exception:
        return []


def _find_record(records: list[dict], target_date: str, key: str = "calendar_date") -> dict | None:
    """Find the first record matching a date string."""
    for r in records:
        if r.get(key, "")[:10] == target_date:
            return r
    return None


def _trend_chart(dates: list[str], values: list[float], color: str = "#4A90D9", unit: str = "") -> go.Figure:
    """Create a small trend chart with axes."""
    rgb = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    # Short day labels (Mon, Tue, ...)
    day_labels = []
    for d in dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            day_labels.append(dt.strftime("%a"))
        except ValueError:
            day_labels.append(d[-5:])

    fig = go.Figure(
        go.Scatter(
            x=day_labels,
            y=values,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
            fill="tozeroy",
            fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.15)",
            hovertemplate="%{y}" + (f" {unit}" if unit else "") + "<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=5, r=5, t=5, b=5),
        height=150,
        xaxis=dict(
            tickfont=dict(size=10),
            showgrid=False,
        ),
        yaxis=dict(
            tickfont=dict(size=10),
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render(selected_date: date | None = None):
    """Render the Home page."""

    today = selected_date or date.today()
    today_str = today.isoformat()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_start_str = week_start.isoformat()
    seven_days_ago = today - timedelta(days=6)
    seven_days_ago_str = seven_days_ago.isoformat()

    # ── Section 1: Today's Metrics ────────────────────────────────────────
    st.header("Today's Metrics")

    tr_data = _safe_get(api_client.get_training_readiness, start_date=today_str, end_date=today_str, limit=1)
    sleep = _safe_get(api_client.get_sleep_data, start_date=today_str, end_date=today_str, limit=1)
    bb = _safe_get(api_client.get_body_battery, start_date=today_str, end_date=today_str, limit=1)
    hrv = _safe_get(api_client.get_hrv_data, start_date=today_str, end_date=today_str, limit=1)

    today_tr = _find_record(tr_data, today_str)
    today_sleep = _find_record(sleep, today_str)
    today_bb = _find_record(bb, today_str)
    today_hrv = _find_record(hrv, today_str)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        score = today_tr.get("score") if today_tr else None
        st.metric("Readiness Score", f"{score}" if score is not None else "—")
    with col2:
        ss = today_sleep.get("sleep_score") if today_sleep else None
        st.metric("Sleep Score", f"{ss}" if ss else "—")
    with col3:
        bbv = (today_bb.get("highest_value") or today_bb.get("charged_value")) if today_bb else None
        st.metric("Body Battery", f"{bbv}" if bbv else "—")
    with col4:
        hrv_val = None
        if today_hrv:
            hrv_val = today_hrv.get("weekly_avg") or today_hrv.get("last_night_avg") or today_hrv.get("last_night_5_min_high")
        st.metric("HRV", f"{hrv_val}" if hrv_val else "—")

    st.divider()

    # ── Section 3 & 4: Weekly Summary + Recent Activities ─────────────────
    left, right = st.columns(2)

    with left:
        st.header("Weekly Summary")

        week_activities = _safe_get(
            api_client.get_activities,
            start_date=week_start_str,
            end_date=today_str,
            limit=50,
        )

        if week_activities:
            total_duration = sum(a.get("duration_seconds", 0) or 0 for a in week_activities)

            # Count by activity type
            type_counts: dict[str, int] = {}
            for a in week_activities:
                atype = a.get("activity_type") or a.get("sport_type") or "other"
                type_counts[atype] = type_counts.get(atype, 0) + 1

            # Distance and elevation by type
            dist_by_type: dict[str, float] = {}
            elev_by_type: dict[str, float] = {}
            for a in week_activities:
                atype = a.get("activity_type") or a.get("sport_type") or "other"
                dist_by_type[atype] = dist_by_type.get(atype, 0) + (a.get("distance_meters", 0) or 0)
                elev_by_type[atype] = elev_by_type.get(atype, 0) + (a.get("elevation_gain_meters", 0) or 0)

            st.metric("Duration", format_duration(total_duration))
            for atype, dist in sorted(dist_by_type.items(), key=lambda x: -x[1]):
                if dist > 0:
                    elev = elev_by_type.get(atype, 0)
                    elev_str = f"{elev:.0f} m D+" if elev > 0 else None
                    st.metric(f"{sport_icon(atype)} {atype.replace('_', ' ').title()}", f"{dist / 1000:.1f} km", delta=elev_str)
            st.metric("Activities", str(len(week_activities)))
            st.markdown(" · ".join(f"{sport_icon(t)} {t.replace('_', ' ').title()} ×{n}" for t, n in sorted(type_counts.items(), key=lambda x: -x[1])))
        else:
            st.info("No activities this week yet.")

    with right:
        st.header("Recent Activities")

        recent = _safe_get(
            api_client.get_activities,
            start_date=(today - timedelta(days=30)).isoformat(),
            end_date=today_str,
            limit=7,
        )

        if recent:
            for act in recent:
                icon = sport_icon(act.get("sport_type"))
                name = act.get("activity_name", "Activity")
                dur = format_duration(act.get("duration_seconds"))
                dist = act.get("distance_meters")
                dist_str = f"{dist / 1000:.1f} km" if dist else ""

                parts = [p for p in [dur, dist_str] if p]
                st.markdown(f"{icon} **{name}** — {' · '.join(parts)}")
        else:
            st.info("No recent activities.")

    st.divider()

    # ── Section 5: 7-Day Trends ───────────────────────────────────────────
    st.header("7-Day Trends")

    daily_7d = _safe_get(
        api_client.get_daily_summary,
        start_date=seven_days_ago_str,
        end_date=today_str,
        limit=7,
    )
    sleep_7d = _safe_get(
        api_client.get_sleep_data,
        start_date=seven_days_ago_str,
        end_date=today_str,
        limit=7,
    )
    bb_7d = _safe_get(
        api_client.get_body_battery,
        start_date=seven_days_ago_str,
        end_date=today_str,
        limit=7,
    )
    body_7d = _safe_get(
        api_client.get_body_composition,
        start_date=seven_days_ago_str,
        end_date=today_str,
        limit=7,
    )
    tr_7d = _safe_get(
        api_client.get_training_readiness,
        start_date=seven_days_ago_str,
        end_date=today_str,
        limit=7,
    )

    def _extract_series(records, *fields, date_key="calendar_date"):
        """Extract dates and values, trying each field name in order."""
        sorted_recs = sorted(records, key=lambda r: (r.get(date_key) or "")[:10])
        dates = []
        values = []
        for r in sorted_recs:
            dates.append((r.get(date_key) or "")[:10])
            val = None
            for f in fields:
                val = r.get(f)
                if val is not None:
                    break
            values.append(val or 0)
        return dates, values

    _chart_cfg = {"displayModeBar": False}

    t1, t2, t3, t4, t5, t6 = st.columns(6)

    with t1:
        st.caption("Steps")
        dates, vals = _extract_series(daily_7d, "total_steps")
        if any(vals):
            st.plotly_chart(_trend_chart(dates, vals, "#4A90D9", "steps"), use_container_width=True, config=_chart_cfg)
        else:
            st.write("—")

    with t2:
        st.caption("Sleep Score")
        dates, vals = _extract_series(sleep_7d, "sleep_score")
        if any(vals):
            st.plotly_chart(_trend_chart(dates, vals, "#9B59B6", "/ 100"), use_container_width=True, config=_chart_cfg)
        else:
            st.write("—")

    with t3:
        st.caption("Resting HR")
        dates, vals = _extract_series(daily_7d, "resting_heart_rate")
        if any(vals):
            st.plotly_chart(_trend_chart(dates, vals, "#E74C3C", "bpm"), use_container_width=True, config=_chart_cfg)
        else:
            st.write("—")

    with t4:
        st.caption("Body Battery")
        dates, vals = _extract_series(bb_7d, "highest_value", "charged_value")
        if any(vals):
            st.plotly_chart(_trend_chart(dates, vals, "#2ECC71"), use_container_width=True, config=_chart_cfg)
        else:
            st.write("—")

    with t5:
        st.caption("Weight")
        dates, vals = _extract_series(body_7d, "weight_kg", date_key="timestamp")
        if any(vals):
            st.plotly_chart(_trend_chart(dates, vals, "#F39C12", "kg"), use_container_width=True, config=_chart_cfg)
        else:
            st.write("—")

    with t6:
        st.caption("Training Readiness")
        dates, vals = _extract_series(tr_7d, "score")
        if any(vals):
            st.plotly_chart(_trend_chart(dates, vals, "#E67E22"), use_container_width=True, config=_chart_cfg)
        else:
            st.write("—")
