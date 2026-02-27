"""Tests for HR zone calculator."""
import pytest
from src.training.hr_zones import calculate_hr_zones, estimate_max_hr, get_zone_for_session_type
from src.training.models import SessionType


def test_estimate_max_hr():
    assert estimate_max_hr(30) == 190
    assert estimate_max_hr(40) == 180
    assert estimate_max_hr(50) == 170


def test_calculate_hr_zones_karvonen():
    """Karvonen: target = fc_repos + (HRR × %)."""
    zones = calculate_hr_zones(fc_max=190, fc_repos=60)
    # HRR = 130
    assert len(zones) == 5
    # Z1: 60 + 130*0.50 = 125, 60 + 130*0.60 = 138
    assert zones[0].zone == 1
    assert zones[0].hr_min == 125
    assert zones[0].hr_max == 138
    # Z5: 60 + 130*0.90 = 177, 60 + 130*1.0 = 190
    assert zones[4].zone == 5
    assert zones[4].hr_min == 177
    assert zones[4].hr_max == 190


def test_calculate_hr_zones_age_fallback():
    zones = calculate_hr_zones(age=30)
    assert len(zones) == 5
    # fc_max = 190, fc_repos = 60 (default)
    assert zones[0].hr_min == 125


def test_calculate_hr_zones_missing_both():
    with pytest.raises(ValueError):
        calculate_hr_zones()


def test_get_zone_for_session_type():
    assert get_zone_for_session_type(SessionType.REST) == 1
    assert get_zone_for_session_type(SessionType.REC) == 1
    assert get_zone_for_session_type(SessionType.EF) == 2
    assert get_zone_for_session_type(SessionType.SL) == 2
    assert get_zone_for_session_type(SessionType.TMP) == 3
    assert get_zone_for_session_type(SessionType.COT) == 3
    assert get_zone_for_session_type(SessionType.INT) == 4
    assert get_zone_for_session_type(SessionType.RMU) == 2
    assert get_zone_for_session_type(SessionType.DESC) == 2
