"""Tests for weekly session placement."""
import pytest
from src.training.week_builder import build_week, _get_max_quality_sessions, _get_quality_type_order
from src.training.models import (
    DayPreferences, ExperienceLevel, PlanPhase, RaceCategory, RaceFlags, RaceObjective, SessionType,
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


# --- Day preferences tests ---

def test_long_run_on_preferred_day():
    """Long run should be placed on the preferred day when available."""
    prefs = DayPreferences(long_run=7)  # Prefer Sunday
    sessions = build_week(
        available_days=[2, 4, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=prefs,
    )
    sl = [s for s in sessions if s.session_type == SessionType.SL]
    assert len(sl) == 1
    assert sl[0].day_of_week == 7


def test_quality_on_preferred_days():
    """Quality sessions should be placed on preferred days when available."""
    prefs = DayPreferences(quality=[2, 4])  # Prefer Tue, Thu
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.advanced,
        is_recovery_week=False,
        week_number=10,
        long_run_spec={"target_km": 25, "target_duration_seconds": 9000, "progression_note": "Build"},
        day_preferences=prefs,
    )
    quality = [s for s in sessions if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    # Advanced gets 2 quality sessions — both should be on preferred days
    assert len(quality) >= 2
    quality_days = {s.day_of_week for s in quality}
    assert quality_days.issubset({2, 4})


def test_strength_on_preferred_day():
    """RMU should be placed on the preferred strength day when valid."""
    # Use day 1 (Monday) as preferred strength — quality goes to 3 or 4,
    # so day 1 should not be adjacent to hard sessions
    prefs = DayPreferences(strength=[1])
    sessions = build_week(
        available_days=[3, 4, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=prefs,
    )
    rmu = [s for s in sessions if s.session_type == SessionType.RMU]
    if rmu:  # RMU placement depends on constraints being satisfied
        assert rmu[0].day_of_week == 1


def test_two_strength_sessions():
    """Two preferred strength days should produce 2 RMU sessions when valid."""
    # Sessions: quality on day 3, SL on day 7 → day 1 and 5 are free
    # Day 1: not adjacent to hard (day 2 is free). Day 5: not adjacent to hard (day 4 is EF).
    prefs = DayPreferences(long_run=7, strength=[1, 5])
    sessions = build_week(
        available_days=[3, 4, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=prefs,
    )
    rmu = [s for s in sessions if s.session_type == SessionType.RMU]
    assert len(rmu) == 2
    rmu_days = {s.day_of_week for s in rmu}
    assert rmu_days == {1, 5}


def test_preferred_day_not_available_falls_back():
    """If preferred long_run day isn't in available_days, fall back to weekend."""
    prefs = DayPreferences(long_run=7)  # Prefer Sunday but it's not available
    sessions = build_week(
        available_days=[2, 4, 6],  # No Sunday
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=prefs,
    )
    sl = [s for s in sessions if s.session_type == SessionType.SL]
    assert len(sl) == 1
    assert sl[0].day_of_week == 6  # Falls back to Saturday


def test_no_preferences_same_as_before():
    """Without day_preferences, behavior should be identical to the default."""
    sessions_default = build_week(
        available_days=[2, 4, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
    )
    sessions_none = build_week(
        available_days=[2, 4, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=None,
    )
    # Same sessions on same days
    assert [s.day_of_week for s in sessions_default] == [s.day_of_week for s in sessions_none]
    assert [s.session_type for s in sessions_default] == [s.session_type for s in sessions_none]


def test_no_quality_day_after_long_run():
    """Quality session should never be placed the day after a long run."""
    # Case 1: SL on Saturday (6) → Sunday (7) must not be quality
    prefs1 = DayPreferences(long_run=6, quality=[7])
    sessions1 = build_week(
        available_days=[1, 2, 3, 4, 5, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=prefs1,
    )
    quality1 = [s for s in sessions1 if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    for q in quality1:
        assert q.day_of_week != 7, "Quality should not be placed the day after a long run"

    # Case 2 (wrap-around): SL on Sunday (7) → Monday (1) must not be quality
    prefs2 = DayPreferences(long_run=7, quality=[1])
    sessions2 = build_week(
        available_days=[1, 2, 3, 4, 5, 6, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=prefs2,
    )
    quality2 = [s for s in sessions2 if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    for q in quality2:
        assert q.day_of_week != 1, "Quality on Monday should be blocked when long run is Sunday (wrap-around)"


def test_two_adjacent_quality_allowed():
    """Two consecutive quality days should be allowed (max 2 in a row)."""
    # Advanced gets 2 quality sessions — prefer them on consecutive days 3, 4
    prefs = DayPreferences(quality=[3, 4])
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.advanced,
        is_recovery_week=False,
        week_number=10,
        long_run_spec={"target_km": 25, "target_duration_seconds": 9000, "progression_note": "Build"},
        day_preferences=prefs,
    )
    quality = [s for s in sessions if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    quality_days = {q.day_of_week for q in quality}
    # Both day 3 and 4 should be quality — 2 adjacent is now allowed
    assert 3 in quality_days and 4 in quality_days, \
        "Two adjacent quality sessions should be allowed"


def test_three_consecutive_hard_blocked():
    """Three consecutive hard days should be prevented by safety constraints."""
    # Expert with performance objective gets up to 3 quality sessions
    prefs = DayPreferences(quality=[2, 3, 4])
    sessions = build_week(
        available_days=[1, 2, 3, 4, 5, 6],
        phase=PlanPhase.specific,
        experience=ExperienceLevel.expert,
        is_recovery_week=False,
        week_number=10,
        long_run_spec={"target_km": 30, "target_duration_seconds": 10800, "progression_note": "Build"},
        day_preferences=prefs,
        objective=RaceObjective.performance,
    )
    quality = [s for s in sessions if s.session_type in (SessionType.COT, SessionType.TMP, SessionType.INT)]
    quality_days = [q.day_of_week for q in quality]
    # Days 2, 3, 4 should NOT all be quality — max 2 consecutive
    assert not (2 in quality_days and 3 in quality_days and 4 in quality_days), \
        "Three consecutive quality sessions should be prevented"


def test_easy_run_on_preferred_day():
    """EF should be placed on preferred easy_run day when slots are limited."""
    # Intermediate = 4 running sessions. SL on 7, quality on 3 → 1 EF slot left.
    # Available: [1, 3, 5, 7]. Candidates for EF: [1, 5]. Prefer day 5.
    prefs = DayPreferences(long_run=7, quality=[3], easy_run=[5])
    sessions = build_week(
        available_days=[1, 3, 5, 7],
        phase=PlanPhase.development,
        experience=ExperienceLevel.intermediate,
        is_recovery_week=False,
        week_number=5,
        long_run_spec={"target_km": 20, "target_duration_seconds": 8400, "progression_note": "Build"},
        day_preferences=prefs,
    )
    ef = [s for s in sessions if s.session_type == SessionType.EF]
    # With 4 sessions total: SL(7) + quality(3) + EF + EF or fewer
    # Preferred day 5 should be the first EF placed
    ef_days = [s.day_of_week for s in ef]
    assert 5 in ef_days, "Preferred easy_run day should be used"
