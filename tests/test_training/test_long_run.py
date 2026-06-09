"""Tests for long run calculator."""
import pytest
from src.training.long_run import calculate_long_run, scale_long_run_spec
from src.training.models import ExperienceLevel, PlanPhase, RaceObjective
from src.training.pace_calculator import compute_paces


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


# --- Road marathon variants (Lot 3) ---------------------------------------

_BRUGGE_KM = 42.195
# Phase per week for a 16-week intermediate marathon block.
_PHASES_16W = (
    [PlanPhase.base] * 4
    + [PlanPhase.development] * 5
    + [PlanPhase.specific] * 5
    + [PlanPhase.taper] * 2
)


def _road_lr(week, phase, recovery=False, pace_set=None):
    return calculate_long_run(
        week_number=week, total_weeks=16, phase=phase,
        is_recovery_week=recovery, experience=ExperienceLevel.intermediate,
        race_distance_km=_BRUGGE_KM, current_long_run_km=15,
        discipline="road", pace_set=pace_set,
    )


def test_road_never_exceeds_35km():
    """Road long run is hard-capped at 35 km in every week/phase."""
    for week in range(1, 17):
        result = _road_lr(week, _PHASES_16W[week - 1])
        assert result["target_km"] <= 35.0


def test_road_peak_in_28_35_range():
    """The 16-week road block peaks between 28 and 35 km (spec §3)."""
    peak = max(
        _road_lr(week, _PHASES_16W[week - 1])["target_km"] for week in range(1, 17)
    )
    assert 28.0 <= peak <= 35.0


def test_road_specific_has_marathon_pace_block():
    """Specific-phase long runs carry a marathon-pace finish block."""
    result = _road_lr(week=11, phase=PlanPhase.specific)
    assert result["marathon_pace_block_km"] > 0
    assert result["variant"] in {"marathon_pace_finish", "fast_finish"}
    assert result["hr_zone"] == "Z2"


def test_road_base_is_progressive_easy():
    """Base/development long runs are easy with no marathon-pace block."""
    result = _road_lr(week=2, phase=PlanPhase.base)
    assert result["variant"] == "progressive_easy"
    assert result["marathon_pace_block_km"] == 0.0


def test_road_taper_reduces_volume_but_keeps_intensity():
    """Taper cuts volume vs specific peak yet keeps a marathon-pace block."""
    specific_peak = _road_lr(week=12, phase=PlanPhase.specific)["target_km"]
    taper = _road_lr(week=16, phase=PlanPhase.taper)
    assert taper["target_km"] < specific_peak
    assert taper["variant"] == "taper_quality"
    assert taper["marathon_pace_block_km"] > 0  # intensity kept (Wang 2023)


def test_road_recovery_week_is_easy_only():
    """Recovery weeks drop the marathon-pace block entirely."""
    result = _road_lr(week=8, phase=PlanPhase.development, recovery=True)
    assert result["variant"] == "recovery_easy"
    assert result["marathon_pace_block_km"] == 0.0


def test_road_pace_labels_from_pace_set():
    """When a PaceSet is supplied, EF/MPR labels are surfaced on the run."""
    paces = compute_paces(14.5, objective=RaceObjective.performance)
    result = _road_lr(week=11, phase=PlanPhase.specific, pace_set=paces)
    assert result["easy_pace"] == paces.zones["EF"].label
    assert result["marathon_pace"] == paces.zones["MPR"].label


def _implied_pace_sec(spec: dict) -> float:
    """Pace in seconds/km implied by a spec's distance and duration."""
    return spec["target_duration_seconds"] / spec["target_km"]


def test_scale_long_run_keeps_distance_and_duration_coherent():
    """Scaling shrinks distance and duration together: implied pace is preserved."""
    paces = compute_paces(14.5, objective=RaceObjective.performance)
    spec = _road_lr(week=11, phase=PlanPhase.specific, pace_set=paces)

    scaled = scale_long_run_spec(spec, 0.6)

    assert scaled["target_km"] == pytest.approx(spec["target_km"] * 0.6, abs=0.1)
    assert scaled["marathon_pace_block_km"] < spec["marathon_pace_block_km"]
    # The whole point: pace stays the same after scaling (was the bug — duration
    # was trimmed while distance stayed, yielding impossible paces).
    assert _implied_pace_sec(scaled) == pytest.approx(_implied_pace_sec(spec), rel=0.05)


def test_scale_long_run_noop_when_scale_ge_one():
    """A scale >= 1 returns the spec unchanged (no inflation)."""
    spec = _road_lr(week=6, phase=PlanPhase.development)
    assert scale_long_run_spec(spec, 1.0) is spec
    assert scale_long_run_spec(spec, 1.5) is spec


def test_scale_long_run_trail_spec_scales_duration():
    """Trail specs (no per-km pace) still scale distance and duration together."""
    spec = calculate_long_run(
        week_number=10, total_weeks=12, phase=PlanPhase.specific,
        is_recovery_week=False, experience=ExperienceLevel.expert,
        race_distance_km=100, current_long_run_km=25,
    )
    scaled = scale_long_run_spec(spec, 0.5)
    assert scaled["target_km"] == pytest.approx(spec["target_km"] * 0.5, abs=0.1)
    assert scaled["target_duration_seconds"] < spec["target_duration_seconds"]
    assert _implied_pace_sec(scaled) == pytest.approx(_implied_pace_sec(spec), rel=0.05)


def test_road_taper_note_is_not_progressive_build():
    """Taper weeks must not carry the misleading 'progressive build' note."""
    taper = _road_lr(week=16, phase=PlanPhase.taper)
    assert "build" not in taper["progression_note"].lower()
    assert "taper" in taper["progression_note"].lower()


def test_trail_unaffected_by_road_changes():
    """Trail path keeps its original keys and no road metadata leaks in."""
    result = calculate_long_run(
        week_number=10, total_weeks=12, phase=PlanPhase.specific,
        is_recovery_week=False, experience=ExperienceLevel.expert,
        race_distance_km=100, current_long_run_km=25,
    )
    assert "variant" not in result
    assert result["target_km"] <= 80.0
