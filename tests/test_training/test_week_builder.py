"""Tests for weekly session placement."""
import pytest
from src.training.week_builder import build_week
from src.training.models import ExperienceLevel, PlanPhase, SessionType


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
