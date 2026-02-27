"""Tests for periodization engine."""
import pytest
from src.training.periodization import build_periodization, get_phase_volume_factor
from src.training.models import ExperienceLevel, PlanPhase, RaceCategory


def test_12_weeks_intermediate():
    weeks = build_periodization(12, ExperienceLevel.intermediate, RaceCategory.trail_moyen)
    assert len(weeks) == 12
    # Check phases are in order
    phases = [w.phase for w in weeks]
    assert phases[0] == PlanPhase.base
    assert phases[-1] == PlanPhase.taper


def test_16_weeks_advanced():
    weeks = build_periodization(16, ExperienceLevel.advanced, RaceCategory.ultra)
    assert len(weeks) == 16
    # Ultra: more specific phase
    phases = [w.phase for w in weeks]
    assert PlanPhase.specific in phases


def test_8_weeks_beginner():
    weeks = build_periodization(8, ExperienceLevel.beginner, RaceCategory.trail_court)
    assert len(weeks) == 8
    # Beginner: recovery every 2 weeks
    recovery_weeks = [w for w in weeks if w.is_recovery_week]
    assert len(recovery_weeks) >= 2


def test_minimum_weeks():
    with pytest.raises(ValueError):
        build_periodization(5, ExperienceLevel.intermediate, RaceCategory.trail_court)


def test_maximum_weeks():
    with pytest.raises(ValueError):
        build_periodization(31, ExperienceLevel.intermediate, RaceCategory.trail_court)


def test_taper_at_least_1_week():
    weeks = build_periodization(6, ExperienceLevel.beginner, RaceCategory.trail_court)
    taper_weeks = [w for w in weeks if w.phase == PlanPhase.taper]
    assert len(taper_weeks) >= 1


def test_last_week_is_recovery():
    weeks = build_periodization(12, ExperienceLevel.intermediate, RaceCategory.trail_moyen)
    assert weeks[-1].is_recovery_week


def test_volume_factor_base():
    assert get_phase_volume_factor(PlanPhase.base, False) == 0.7


def test_volume_factor_recovery():
    factor = get_phase_volume_factor(PlanPhase.specific, True)
    assert factor == pytest.approx(0.6, abs=0.01)


def test_volume_factor_taper():
    assert get_phase_volume_factor(PlanPhase.taper, False) == 0.5


def test_20_weeks_expert():
    weeks = build_periodization(20, ExperienceLevel.expert, RaceCategory.ultra_longue)
    assert len(weeks) == 20
    # Expert: recovery every 4 weeks
    phases_with_recovery = [(w.week_number, w.is_recovery_week) for w in weeks]
    # Should have some recovery weeks but not too many
    recovery_count = sum(1 for w in weeks if w.is_recovery_week)
    assert recovery_count >= 3
