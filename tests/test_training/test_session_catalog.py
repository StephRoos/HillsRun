"""Tests for session catalog with race flag adaptations."""
from src.training.session_catalog import get_phase_session_types
from src.training.models import (
    ExperienceLevel, PlanPhase, RaceCategory, RaceFlags, SessionType,
)


def _high_dplus_flags():
    return RaceFlags(category=RaceCategory.trail_moyen, high_dplus=True)


def _technical_flags():
    return RaceFlags(category=RaceCategory.trail_court, technical=True)


def _high_altitude_flags():
    return RaceFlags(category=RaceCategory.ultra, high_altitude=True)


def test_base_phase_no_flags():
    """Base phase without flags should not include COT for beginners."""
    types = get_phase_session_types(PlanPhase.base, ExperienceLevel.beginner)
    assert SessionType.COT not in types


def test_base_phase_high_dplus_adds_cot():
    """High D+ flag should add COT to base phase for all levels."""
    types = get_phase_session_types(PlanPhase.base, ExperienceLevel.beginner, _high_dplus_flags())
    assert SessionType.COT in types


def test_development_high_dplus_cot_before_int():
    """In development, COT should appear before INT for high D+ races."""
    types = get_phase_session_types(PlanPhase.development, ExperienceLevel.intermediate, _high_dplus_flags())
    assert SessionType.COT in types
    assert SessionType.INT in types
    assert types.index(SessionType.COT) < types.index(SessionType.INT)


def test_development_technical_adds_desc():
    """Technical flag should add DESC to development phase."""
    types = get_phase_session_types(PlanPhase.development, ExperienceLevel.intermediate, _technical_flags())
    assert SessionType.DESC in types


def test_base_technical_no_desc_for_beginner():
    """Technical flag should not add DESC to base phase for beginners."""
    types = get_phase_session_types(PlanPhase.base, ExperienceLevel.beginner, _technical_flags())
    assert SessionType.DESC not in types


def test_base_technical_adds_desc_for_advanced():
    """Technical flag should add DESC to base phase for advanced."""
    types = get_phase_session_types(PlanPhase.base, ExperienceLevel.advanced, _technical_flags())
    assert SessionType.DESC in types


def test_no_flags_backward_compatible():
    """Without flags, behavior should match original implementation."""
    types_no_flags = get_phase_session_types(PlanPhase.development, ExperienceLevel.intermediate)
    assert SessionType.EF in types_no_flags
    assert SessionType.SL in types_no_flags
    assert SessionType.TMP in types_no_flags
    assert SessionType.INT in types_no_flags
    assert SessionType.COT in types_no_flags
