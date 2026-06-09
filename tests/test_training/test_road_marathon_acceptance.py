"""Pure-function acceptance suite for the road-marathon engine (spec 02 §8).

These tests assert directly on the pure functions (no DB) for the locked athlete
profile: Marathon de Brugge, intermediate, VMA 14.5, objective performance,
target 3h30. They are the regression anchor for the whole road path.
"""

import pytest

from src.training.long_run import calculate_long_run
from src.training.models import (
    DayPreferences,
    ExperienceLevel,
    PlanPhase,
    RaceCategory,
    RaceObjective,
    SessionType,
)
from src.training.pace_calculator import compute_paces, format_pace
from src.training.race_classifier import classify_race
from src.training.session_catalog import get_phase_session_types
from src.training.week_builder import build_week

# --- Locked profile constants ---
VMA = 14.5
MARATHON_KM = 42.195
TARGET_TIME_S = 12600  # 3h30


def _road_flags():
    return classify_race(
        distance_km=MARATHON_KM,
        elevation_gain_m=0,
        technical_percent=0,
        discipline="road",
    )


# ---------------------------------------------------------------------------
# 1. Classification
# ---------------------------------------------------------------------------
def test_brugge_classifies_as_road_marathon():
    flags = _road_flags()
    assert flags.category == RaceCategory.road_marathon
    assert flags.is_road_marathon is True
    assert flags.is_ultra is False
    assert flags.high_dplus is False
    assert flags.technical is False


# ---------------------------------------------------------------------------
# 2. Pace calculator (VMA 14.5 + performance)
# ---------------------------------------------------------------------------
def test_marathon_pace_is_4_59():
    paces = compute_paces(VMA, RaceObjective.performance, TARGET_TIME_S)
    mpr = paces.zones["MPR"].sec_per_km_fast
    assert abs(mpr - 299) <= 2  # 4:59/km ±2s
    assert format_pace(mpr) == "4:59"


def test_easy_and_recovery_ranges():
    paces = compute_paces(VMA, RaceObjective.performance, TARGET_TIME_S)
    ef = paces.zones["EF"]
    rec = paces.zones["REC"]
    assert ef.is_range and rec.is_range
    # EF ~5:45–6:05, REC ~6:11–6:34 (slower than EF).
    assert ef.sec_per_km_fast == pytest.approx(345, abs=5)
    assert ef.sec_per_km_slow == pytest.approx(365, abs=5)
    assert rec.sec_per_km_fast > ef.sec_per_km_fast  # recovery is slower


def test_target_time_around_3h30_and_not_optimistic():
    paces = compute_paces(VMA, RaceObjective.performance, TARGET_TIME_S)
    assert abs(paces.target_time_seconds - TARGET_TIME_S) <= 120  # ~3h30
    assert paces.pace_objective_optimistic is False


# ---------------------------------------------------------------------------
# 3. Long run (road) — peak window, MP block, taper reduced
# ---------------------------------------------------------------------------
def test_road_long_run_peak_in_window_never_over_35():
    paces = compute_paces(VMA, RaceObjective.performance, TARGET_TIME_S)
    peak = 0.0
    for phase in (PlanPhase.base, PlanPhase.development, PlanPhase.specific):
        for week in range(1, 17):
            r = calculate_long_run(
                week_number=week,
                total_weeks=16,
                phase=phase,
                is_recovery_week=False,
                experience=ExperienceLevel.intermediate,
                race_distance_km=MARATHON_KM,
                current_long_run_km=28,
                discipline="road",
                pace_set=paces,
            )
            assert r["target_km"] <= 35.0  # absolute road cap
            peak = max(peak, r["target_km"])
    assert 28.0 <= peak <= 35.0


def test_specific_phase_has_marathon_pace_block():
    paces = compute_paces(VMA, RaceObjective.performance, TARGET_TIME_S)
    r = calculate_long_run(
        week_number=12,
        total_weeks=16,
        phase=PlanPhase.specific,
        is_recovery_week=False,
        experience=ExperienceLevel.intermediate,
        race_distance_km=MARATHON_KM,
        current_long_run_km=30,
        discipline="road",
        pace_set=paces,
    )
    assert r["marathon_pace_block_km"] > 0
    assert r["variant"] in ("marathon_pace_finish", "fast_finish")
    assert r["hr_zone"] == "Z2"
    assert r["marathon_pace"] is not None


def test_taper_long_run_reduced_vs_specific():
    paces = compute_paces(VMA, RaceObjective.performance, TARGET_TIME_S)
    common = dict(
        week_number=12,
        total_weeks=16,
        is_recovery_week=False,
        experience=ExperienceLevel.intermediate,
        race_distance_km=MARATHON_KM,
        current_long_run_km=30,
        discipline="road",
        pace_set=paces,
    )
    specific = calculate_long_run(phase=PlanPhase.specific, **common)
    taper = calculate_long_run(phase=PlanPhase.taper, **common)
    assert taper["target_km"] < specific["target_km"]


# ---------------------------------------------------------------------------
# 4. Catalog — no COT/DESC, MPR/TMP/INT present in road specific phase
# ---------------------------------------------------------------------------
def test_road_specific_excludes_cot_desc_includes_mpr():
    flags = _road_flags()
    types = get_phase_session_types(
        PlanPhase.specific, ExperienceLevel.intermediate, flags
    )
    assert SessionType.COT not in types
    assert SessionType.DESC not in types
    assert SessionType.MPR in types
    assert SessionType.TMP in types
    assert SessionType.INT in types


def test_trail_no_flags_still_has_cot():
    # Backward-compat guard: trail default path must keep COT (cf spec §3).
    types = get_phase_session_types(PlanPhase.development, ExperienceLevel.expert, None)
    assert SessionType.COT in types


# ---------------------------------------------------------------------------
# 5. Week builder — honour day preferences, no back-to-back hard days
# ---------------------------------------------------------------------------
def _hard(session_type: SessionType) -> bool:
    return session_type in {
        SessionType.TMP,
        SessionType.INT,
        SessionType.MPR,
        SessionType.COT,
        SessionType.SL,
    }


def test_week_builder_honours_day_preferences_road():
    flags = _road_flags()
    # Run days are Tue(2)/Thu(4)/Sat(6)/Sun(7); strength (Wed=3) is placed on a
    # day OUTSIDE available_days — strength is additive, not a run slot.
    prefs = DayPreferences(long_run=7, quality=[4], strength=[3])
    sessions = build_week(
        available_days=[2, 4, 6, 7],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=12,
        long_run_spec={"target_km": 30.0, "target_duration_seconds": 9000},
        race_flags=flags,
        objective=RaceObjective.performance,
        day_preferences=prefs,
    )
    by_day = {s.day_of_week: s.session_type for s in sessions}

    # Long run on Sunday (7), strength on Wednesday (3).
    assert by_day.get(7) == SessionType.SL
    assert by_day.get(3) == SessionType.RMU

    # No two hard days back to back.
    days = sorted(by_day)
    for a, b in zip(days, days[1:]):
        if b - a == 1:
            assert not (_hard(by_day[a]) and _hard(by_day[b])), (
                f"back-to-back hard days {a}->{b}"
            )
