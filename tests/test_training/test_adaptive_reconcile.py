"""Unit tests for the adaptive coach Lot D3 (planned-vs-actual reconciliation).

All read-only. Covers matching tolerance, compliance maths, realized-TSS
aggregation, the informational-only ACWR, and a mocked-pool orchestrator smoke
that asserts no write ever happens.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.training.adaptive.adherence import (
    ACWR_CONTESTED_NOTE,
    bucket_weekly_tss,
    build_session_adherence,
    compute_acwr_informational,
    week_adherence,
)
from src.training.adaptive.queries import reconcile_plan
from src.training.adaptive.workout_matcher import (
    match_workouts,
    sport_category,
)


def _planned(pid, day, sport="road_running", session="EF", dur=3600, dist=10000, tss=60):
    return {
        "id": pid,
        "planned_date": day,
        "sport_type": sport,
        "session_type": session,
        "title": f"{session} session",
        "target_duration_seconds": dur,
        "target_distance_meters": dist,
        "target_tss": tss,
    }


def _activity(aid, ts, sport="running", dur=3500, dist=9800, tss=58):
    return {
        "activity_id": aid,
        "activity_name": "Morning run",
        "activity_type": "running",
        "sport_type": sport,
        "start_timestamp": ts,
        "duration_seconds": dur,
        "distance_meters": dist,
        "training_stress_score": tss,
    }


# ---------------------------------------------------------------------------
# sport_category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sport,expected",
    [
        ("road_running", "run"),
        ("trail_running", "run"),
        ("running", "run"),
        ("cycling", "bike"),
        ("indoor_cycling", "bike"),
        ("lap_swimming", "swim"),
        ("strength_training", "strength"),
        ("yoga", "other"),
    ],
)
def test_sport_category(sport, expected):
    assert sport_category(sport) == expected


# ---------------------------------------------------------------------------
# match_workouts — tolerance
# ---------------------------------------------------------------------------


def test_match_exact_day():
    planned = [_planned(1, date(2026, 6, 2))]
    acts = [_activity(10, datetime(2026, 6, 2, 7, 0))]
    [m] = match_workouts(planned, acts)
    assert m.matched and m.day_offset == 0 and m.activity_id == 10


def test_match_within_one_day():
    planned = [_planned(1, date(2026, 6, 2))]
    acts = [_activity(10, datetime(2026, 6, 3, 7, 0))]
    [m] = match_workouts(planned, acts)
    assert m.matched and m.day_offset == 1


def test_match_outside_tolerance_is_missed():
    planned = [_planned(1, date(2026, 6, 2))]
    acts = [_activity(10, datetime(2026, 6, 4, 7, 0))]
    [m] = match_workouts(planned, acts)
    assert not m.matched and m.activity_id is None


def test_match_sport_category_tolerance():
    # planned road_running matches a generic Garmin "running" activity...
    planned = [_planned(1, date(2026, 6, 2), sport="road_running")]
    acts = [_activity(10, datetime(2026, 6, 2, 7, 0), sport="trail_running")]
    [m] = match_workouts(planned, acts)
    assert m.matched
    # ...but a strength session never matches a run.
    planned2 = [_planned(2, date(2026, 6, 2), sport="strength_training", session="RMU")]
    [m2] = match_workouts(planned2, acts)
    assert not m2.matched


def test_each_activity_matched_once():
    planned = [_planned(1, date(2026, 6, 2)), _planned(2, date(2026, 6, 2))]
    acts = [_activity(10, datetime(2026, 6, 2, 7, 0))]
    m1, m2 = match_workouts(planned, acts)
    assert m1.matched ^ m2.matched  # exactly one consumed the single activity


def test_match_prefers_nearest_day():
    planned = [_planned(1, date(2026, 6, 2))]
    acts = [
        _activity(10, datetime(2026, 6, 3, 7, 0)),  # offset +1
        _activity(11, datetime(2026, 6, 2, 7, 0)),  # offset 0 -> preferred
    ]
    [m] = match_workouts(planned, acts)
    assert m.activity_id == 11 and m.day_offset == 0


# ---------------------------------------------------------------------------
# adherence — compliance & TSS
# ---------------------------------------------------------------------------


def test_build_session_adherence_ratios_and_pace():
    planned = _planned(1, date(2026, 6, 2), dur=3600, dist=10000, tss=60)
    act = _activity(10, datetime(2026, 6, 2, 7, 0), dur=3500, dist=9800, tss=58)
    [m] = match_workouts([planned], [act])
    s = build_session_adherence(m, planned, act)
    assert s.completed
    assert s.planned_pace_sec_per_km == pytest.approx(360.0)
    assert s.actual_pace_sec_per_km == pytest.approx(3500 / 9.8)
    assert s.duration_ratio == pytest.approx(3500 / 3600)
    assert s.distance_ratio == pytest.approx(0.98)


def test_missed_session_has_no_actuals():
    planned = _planned(1, date(2026, 6, 2))
    [m] = match_workouts([planned], [])
    s = build_session_adherence(m, planned, None)
    assert not s.completed
    assert s.actual_duration_seconds is None
    assert s.actual_tss is None


def test_week_adherence_compliance_and_realized_tss():
    planned = [_planned(i, date(2026, 6, 1 + i), tss=50) for i in range(4)]
    # Complete only 3 of the 4, each with actual TSS 40.
    acts = [
        _activity(100 + i, datetime(2026, 6, 1 + i, 7, 0), tss=40) for i in range(3)
    ]
    matches = match_workouts(planned, acts)
    by_id = {p["id"]: p for p in planned}
    by_act = {a["activity_id"]: a for a in acts}
    sessions = [
        build_session_adherence(
            m, by_id[m.planned_id], by_act.get(m.activity_id) if m.matched else None
        )
        for m in matches
    ]
    wk = week_adherence(sessions, week_number=1)
    assert wk.planned_sessions == 4
    assert wk.completed_sessions == 3
    assert wk.compliance_pct == 75.0
    assert wk.planned_tss == 200.0
    assert wk.realized_tss == 120.0  # only completed sessions count


# ---------------------------------------------------------------------------
# ACWR — informational only
# ---------------------------------------------------------------------------


def test_bucket_weekly_tss_oldest_first():
    end = date(2026, 6, 28)
    acts = [
        _activity(1, datetime(2026, 6, 28, 7, 0), tss=100),  # current week
        _activity(2, datetime(2026, 6, 1, 7, 0), tss=50),  # 27 days back -> oldest
        _activity(3, datetime(2026, 5, 1, 7, 0), tss=999),  # out of 28d window
    ]
    buckets = bucket_weekly_tss(acts, end)
    assert len(buckets) == 4
    assert buckets[-1] == 100.0  # most recent
    assert buckets[0] == 50.0  # oldest
    assert 999.0 not in buckets


def test_compute_acwr_has_note_and_value():
    acwr = compute_acwr_informational([50.0, 50.0, 50.0, 100.0])
    assert acwr is not None
    assert acwr["acute_tss"] == 100.0
    assert acwr["chronic_tss"] == 62.5
    assert acwr["value"] == pytest.approx(1.6)
    assert acwr["note"] == ACWR_CONTESTED_NOTE


def test_compute_acwr_empty_is_none():
    assert compute_acwr_informational([]) is None


# ---------------------------------------------------------------------------
# orchestrator smoke — mocked pool, asserts no write
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconcile_plan_read_only_smoke():
    plan_row = {
        "id": 5,
        "user_id": 1,
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 8, 31),
        "total_weeks": 12,
    }
    # Week 1 window = 2026-06-01..06-07.
    planned = [
        _planned(101, date(2026, 6, 2), tss=60),
        _planned(102, date(2026, 6, 5), session="MPR", dur=5400, dist=18000, tss=95),
    ]
    window_acts = [_activity(201, datetime(2026, 6, 2, 7, 0), tss=58)]  # matches 101
    acwr_acts = [_activity(301, datetime(2026, 6, 7, 7, 0), tss=58)]

    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=plan_row)
    pool.fetch = AsyncMock(side_effect=[planned, window_acts, acwr_acts])

    report = await reconcile_plan(pool, 5, 1, week_number=1)

    assert report is not None
    assert report["plan_id"] == 5
    assert report["week_number"] == 1
    assert report["window"] == {"start": "2026-06-01", "end": "2026-06-07"}
    adh = report["adherence"]
    assert adh["planned_sessions"] == 2
    assert adh["completed_sessions"] == 1
    assert adh["compliance_pct"] == 50.0
    assert adh["planned_tss"] == 155.0
    assert adh["realized_tss"] == 58.0
    assert adh["acwr_informational"]["note"] == ACWR_CONTESTED_NOTE
    assert len(report["matches"]) == 2
    # Read-only: never executed a write statement.
    pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_reconcile_plan_missing_returns_none():
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=None)  # plan not found / not owned
    pool.fetch = AsyncMock()
    report = await reconcile_plan(pool, 999, 1, week_number=1)
    assert report is None
    pool.fetch.assert_not_called()
