"""Tests for weekly session placement."""
import pytest
from src.training.week_builder import build_week, _get_max_quality_sessions, _get_quality_type_order
from src.training.models import (
    ExperienceLevel, PlanPhase, RaceCategory, RaceFlags, RaceObjective, SessionType,
)


def test_4_days_intermediate():
    sessions = build_week(
        available_days=[2, 4, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
    )
    assert len(sessions) >= 3
    # Long run should be on weekend
    sl_sessions = [s for s in sessions if s.session_type == SessionType.SL]
    assert len(sl_sessions) == 1
    assert sl_sessions[0].day_of_week in [6, 7]


def test_recovery_week_only_easy():
    sessions = build_week(
        available_days=[1, 3, 5, 6],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=True,
        week_number=6,
    )
    hard_types = {SessionType.INT, SessionType.TMP, SessionType.COT}
    for s in sessions:
        assert s.session_type not in hard_types


def test_3_days_beginner():
    sessions = build_week(
        available_days=[2, 5, 6],
        phase=PlanPhase.base,
        experience=ExperienceLevel.beginner,
        is_recovery_week=False,
        week_number=1,
    )
    assert len(sessions) >= 2
    assert len(sessions) <= 4  # 3 sessions + maybe RMU


def test_6_days_expert():
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.expert,
        is_recovery_week=False,
        week_number=15,
        long_run_spec={"target_km": 40, "target_duration_seconds": 13200, "progression_note": "Build"},
    )
    assert len(sessions) >= 5


def test_empty_days_raises():
    with pytest.raises(ValueError):
        build_week(
            available_days=[],
            phase=PlanPhase.base,
            experience=ExperienceLevel.intermediate,
            is_recovery_week=False,
            week_number=1,
        )


def test_sessions_sorted_by_day():
    sessions = build_week(
        available_days=[1, 3, 5, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.advanced,
        is_recovery_week=False,
        week_number=8,
    )
    days = [s.day_of_week for s in sessions]
    assert days == sorted(days)


# --- Race flags tests ---

def _high_dplus_flags():
    return RaceFlags(category=RaceCategory.trail_moyen, high_dplus=True)


def _technical_flags():
    return RaceFlags(category=RaceCategory.trail_court, technical=True)


def test_high_dplus_prioritizes_cot():
    """High D+ races should prioritize COT over TMP/INT."""
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=8,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        race_flags=_high_dplus_flags(),
    )
    quality = [s for s in sessions if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    assert len(quality) >= 1
    # COT should be the first quality session placed
    assert quality[0].session_type == SessionType.COT


def test_high_dplus_long_run_has_elevation():
    """Long runs for high D+ races should have elevation gain targets."""
    sessions = build_week(
        available_days=[2, 4, 6, 7],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.advanced,
        is_recovery_week=False,
        week_number=10,
        long_run_spec={"target_km": 30, "target_duration_seconds": 10800, "progression_note": "Build"},
        race_flags=_high_dplus_flags(),
    )
    sl = [s for s in sessions if s.session_type == SessionType.SL]
    assert len(sl) == 1
    assert sl[0].target_elevation_gain_m is not None
    assert sl[0].target_elevation_gain_m > 0


def test_technical_race_adds_desc():
    """Technical races should include DESC sessions in specific phase."""
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.advanced,
        is_recovery_week=False,
        week_number=12,
        long_run_spec={"target_km": 25, "target_duration_seconds": 9000, "progression_note": "Build"},
        race_flags=_technical_flags(),
    )
    types = {s.session_type for s in sessions}
    assert SessionType.DESC in types


def test_no_flags_no_elevation_on_long_run():
    """Without race flags, long runs should not have elevation targets."""
    sessions = build_week(
        available_days=[2, 4, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
    )
    sl = [s for s in sessions if s.session_type == SessionType.SL]
    assert sl[0].target_elevation_gain_m is None


# --- Objective tests ---

def test_finish_objective_max_1_quality():
    """Finish objective should limit quality to 1 even for advanced."""
    max_q = _get_max_quality_sessions(ExperienceLevel.advanced, RaceObjective.finish)
    assert max_q == 1


def test_performance_objective_allows_3_quality_expert():
    """Performance objective should allow up to 3 for expert."""
    max_q = _get_max_quality_sessions(ExperienceLevel.expert, RaceObjective.performance)
    assert max_q == 3


def test_midpack_default_quality():
    """Midpack (default) should keep standard quality limits."""
    max_q = _get_max_quality_sessions(ExperienceLevel.advanced, RaceObjective.midpack)
    assert max_q == 2


# --- Multiple quality sessions tests ---

def test_advanced_gets_2_quality_sessions():
    """Advanced athletes should get 2 quality sessions in specific phase."""
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.advanced,
        is_recovery_week=False,
        week_number=12,
        long_run_spec={"target_km": 30, "target_duration_seconds": 10800, "progression_note": "Build"},
    )
    quality = [s for s in sessions if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    assert len(quality) >= 2


def test_beginner_stays_at_1_quality():
    """Beginners should still only get 1 quality session max."""
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.beginner,
        is_recovery_week=False,
        week_number=10,
        long_run_spec={"target_km": 15, "target_duration_seconds": 7200, "progression_note": "Build"},
    )
    quality = [s for s in sessions if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    assert len(quality) <= 1


# --- Quality type ordering ---

def test_quality_order_default():
    """Default quality order should be TMP, INT, COT."""
    order = _get_quality_type_order([SessionType.TMP, SessionType.INT, SessionType.COT])
    assert order[0] == SessionType.TMP


def test_quality_order_high_dplus():
    """High D+ should put COT first."""
    flags = _high_dplus_flags()
    order = _get_quality_type_order(
        [SessionType.TMP, SessionType.INT, SessionType.COT],
        race_flags=flags,
    )
    assert order[0] == SessionType.COT
