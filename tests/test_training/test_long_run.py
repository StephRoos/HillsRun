"""Tests for long run calculator."""
import pytest
from src.training.long_run import calculate_long_run
from src.training.models import ExperienceLevel, PlanPhase


def test_base_phase_cap():
    """Long run in base phase should not exceed 30% of race distance."""
    result = calculate_long_run(
        week_number=4, total_weeks=12, phase=PlanPhase.base,
        is_recovery_week=False, experience=ExperienceLevel.expert,
        race_distance_km=100, current_long_run_km=25,
    )
    assert result["target_km"] <= 30.0  # 30% of 100km


def test_specific_phase_cap():
    """Long run in specific phase capped at 70% of race (max 80km)."""
    result = calculate_long_run(
        week_number=10, total_weeks=12, phase=PlanPhase.specific,
        is_recovery_week=False, experience=ExperienceLevel.expert,
        race_distance_km=170, current_long_run_km=25,
    )
    assert result["target_km"] <= 80.0  # Absolute cap


def test_recovery_week_reduction():
    result = calculate_long_run(
        week_number=4, total_weeks=12, phase=PlanPhase.base,
        is_recovery_week=True, experience=ExperienceLevel.intermediate,
        race_distance_km=50, current_long_run_km=15,
    )
    # Recovery = starting km * 0.6
    assert result["target_km"] < 15.0


def test_duration_estimation():
    result = calculate_long_run(
        week_number=1, total_weeks=12, phase=PlanPhase.base,
        is_recovery_week=False, experience=ExperienceLevel.intermediate,
        race_distance_km=50, current_long_run_km=15,
    )
    # 15km at 7 min/km = 105 min = 6300s
    assert result["target_duration_seconds"] > 0


def test_default_starting_distance():
    result = calculate_long_run(
        week_number=1, total_weeks=12, phase=PlanPhase.base,
        is_recovery_week=False, experience=ExperienceLevel.beginner,
        race_distance_km=30, current_long_run_km=0,
    )
    assert result["target_km"] > 0  # Should use default 10km


def test_invalid_week():
    with pytest.raises(ValueError):
        calculate_long_run(
            week_number=0, total_weeks=12, phase=PlanPhase.base,
            is_recovery_week=False, experience=ExperienceLevel.intermediate,
            race_distance_km=50, current_long_run_km=15,
        )
