"""Tests for the VMA-driven pace calculator (road marathon)."""
import pytest

from src.training.models import RaceObjective
from src.training.pace_calculator import (
    compute_paces,
    compute_paces_from_fitness,
    format_pace,
)


def test_format_pace():
    assert format_pace(299) == "4:59"
    assert format_pace(248) == "4:08"
    assert format_pace(60) == "1:00"


def test_performance_paces_at_vma_14_5():
    """Spec §4 reference table: VMA 14.5, objective performance."""
    paces = compute_paces(14.5, RaceObjective.performance)
    assert paces.pct_marathon == 0.83
    assert paces.pace_source == "vma"

    # MPR (marathon pace) ~4:59/km (±2s).
    mpr = paces.zones["MPR"]
    assert abs(mpr.sec_per_km_fast - 299) <= 2
    assert format_pace(mpr.sec_per_km_fast) == "4:59"

    # TMP ~4:42, INT ~4:08.
    assert abs(paces.zones["TMP"].sec_per_km_fast - 282) <= 2
    assert abs(paces.zones["INT"].sec_per_km_fast - 248) <= 2

    # EF is a range ~5:45–6:05 (HR-bound), REC ~6:11–6:34.
    ef = paces.zones["EF"]
    assert ef.is_range
    assert ef.sec_per_km_fast < ef.sec_per_km_slow  # faster bound is lower s/km
    assert 340 <= ef.sec_per_km_fast <= 350
    assert 360 <= ef.sec_per_km_slow <= 370

    rec = paces.zones["REC"]
    assert rec.is_range
    assert 365 <= rec.sec_per_km_fast <= 375
    assert 388 <= rec.sec_per_km_slow <= 398


def test_target_time_around_3h30():
    """Projected marathon time at performance MPR ≈ 3h30 (12600 s)."""
    paces = compute_paces(14.5, RaceObjective.performance)
    assert abs(paces.target_time_seconds - 12600) <= 60


def test_objective_changes_marathon_fraction():
    finish = compute_paces(14.5, RaceObjective.finish)
    midpack = compute_paces(14.5, RaceObjective.midpack)
    perf = compute_paces(14.5, RaceObjective.performance)
    assert finish.pct_marathon == 0.78
    assert midpack.pct_marathon == 0.80
    assert perf.pct_marathon == 0.83
    # Faster objective → faster (lower s/km) marathon pace.
    assert perf.zones["MPR"].sec_per_km_fast < finish.zones["MPR"].sec_per_km_fast


def test_optimistic_flag_matches_locked_profile():
    """Brugge §2: target 12600 s matches the VMA prediction → not optimistic."""
    matched = compute_paces(14.5, RaceObjective.performance, target_time_seconds=12600)
    assert matched.pace_objective_optimistic is False

    # A clearly faster goal (3h00) than the prediction → flagged optimistic.
    ambitious = compute_paces(14.5, RaceObjective.performance, target_time_seconds=10800)
    assert ambitious.pace_objective_optimistic is True


def test_vo2max_fallback():
    """When VMA is absent, derive it from VO2max (vma ≈ vo2max / 3.5)."""
    # VO2max 50.75 ≈ VMA 14.5.
    paces = compute_paces_from_fitness(
        vma_kmh=None, vo2_max=50.75, objective=RaceObjective.performance
    )
    assert paces.pace_source == "vo2max_estimate"
    assert abs(paces.vma_kmh - 14.5) < 0.1
    assert abs(paces.zones["MPR"].sec_per_km_fast - 299) <= 2


def test_fitness_prefers_measured_vma():
    paces = compute_paces_from_fitness(
        vma_kmh=14.5, vo2_max=99.0, objective=RaceObjective.performance
    )
    assert paces.pace_source == "vma"
    assert paces.vma_kmh == 14.5


def test_fitness_requires_some_signal():
    with pytest.raises(ValueError):
        compute_paces_from_fitness(vma_kmh=None, vo2_max=None)


def test_invalid_vma_raises():
    with pytest.raises(ValueError):
        compute_paces(0)
