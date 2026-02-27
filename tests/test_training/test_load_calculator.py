"""Tests for training load calculator."""
import pytest
from src.training.load_calculator import (
    calculate_session_tss,
    get_weekly_tss_limits,
    validate_weekly_progression,
    calculate_recovery_week_tss,
)
from src.training.models import SessionType, ExperienceLevel


def test_rest_tss_is_zero():
    assert calculate_session_tss(SessionType.REST, 3600) == 0.0


def test_ef_tss_1h_flat():
    """EF 1h flat: (1) × 50 × 1.0 = 50."""
    tss = calculate_session_tss(SessionType.EF, 3600, 0)
    assert tss == 50.0


def test_elevation_factor():
    """EF 1h with 1000m D+: (1) × 50 × 1.15 = 57.5."""
    tss = calculate_session_tss(SessionType.EF, 3600, 1000)
    assert tss == pytest.approx(57.5, abs=0.1)


def test_interval_tss():
    """INT 45min flat: (0.75) × 85 × 1.0 = 63.75."""
    tss = calculate_session_tss(SessionType.INT, 2700, 0)
    assert tss == pytest.approx(63.8, abs=0.1)


def test_weekly_limits_beginner():
    limits = get_weekly_tss_limits(ExperienceLevel.beginner)
    assert limits["min"] == 150
    assert limits["max"] == 350
    assert limits["peak"] == 400


def test_weekly_limits_expert():
    limits = get_weekly_tss_limits(ExperienceLevel.expert)
    assert limits["max"] == 900


def test_progression_valid():
    is_valid, max_tss = validate_weekly_progression(345, 300)
    assert is_valid  # 345 <= 300 * 1.15 = 345
    assert max_tss == 345.0


def test_progression_invalid():
    is_valid, max_tss = validate_weekly_progression(400, 300)
    assert not is_valid
    assert max_tss == 345.0


def test_progression_from_zero():
    is_valid, max_tss = validate_weekly_progression(200, 0)
    assert is_valid


def test_recovery_week_tss():
    recovery = calculate_recovery_week_tss(500.0)
    assert recovery == 300.0  # 500 * 0.6
