"""Progressive long run calculator with phase-based caps.

Trail is the default discipline (D+, 80 km absolute cap, single easy pace). When
``discipline == "road"`` the long run becomes a marathon-specific session: a hard
35 km absolute cap, an easy portion heart-rate-bound to Z2 (pace from the
``PaceSet`` rather than a single value), and phase variants per spec §6
(progressive easy → marathon-pace finish block → reduced-volume taper that keeps
intensity).
"""

from typing import TYPE_CHECKING, Optional

from .models import ExperienceLevel, PlanPhase

if TYPE_CHECKING:  # avoid importing pace_calculator at runtime for trail callers
    from .pace_calculator import PaceSet

# Absolute long-run caps in km (road marathons never exceed 35 km).
_TRAIL_ABSOLUTE_CAP_KM = 80.0
_ROAD_ABSOLUTE_CAP_KM = 35.0

# Marathon-pace finish block (specific phase): up to this many km of the run.
_ROAD_MP_BLOCK_MAX_KM = 12.0
_ROAD_MP_BLOCK_FRACTION = 0.4
# Reduced-volume quality block kept during the taper (spec §6, Wang 2023).
_ROAD_TAPER_MP_BLOCK_MAX_KM = 6.0
_ROAD_TAPER_MP_BLOCK_FRACTION = 0.3

# Fallback road easy pace when no PaceSet is supplied (min/km).
_ROAD_DEFAULT_EASY_PACE_MIN = 6.0


def calculate_long_run(
    week_number: int,
    total_weeks: int,
    phase: PlanPhase,
    is_recovery_week: bool,
    experience: ExperienceLevel,
    race_distance_km: float,
    current_long_run_km: float,
    discipline: str = "trail",
    pace_set: "Optional[PaceSet]" = None,
) -> dict:
    """Calculate target long run for a given week.

    Uses progressive overload adapted to experience level and training phase,
    with phase-specific caps as percentages of race distance. For road marathons
    the run is capped at 35 km, the easy portion is HR-Z2-bound (pace sourced
    from ``pace_set``), and phase variants add a marathon-pace finish block.

    Args:
        week_number: Current week number in training plan (1-indexed).
        total_weeks: Total number of weeks in the training plan.
        phase: Current training phase (base, development, specific, taper).
        is_recovery_week: Whether this is a recovery week.
        experience: Athlete experience level (beginner, intermediate, advanced, expert).
        race_distance_km: Target race distance in kilometers.
        current_long_run_km: Current long run distance in kilometers (from fitness snapshot).
        discipline: ``"trail"`` (default) or ``"road"``. Road enables the 35 km cap,
            Z2 easy pacing and marathon-pace variants.
        pace_set: Optional VMA-derived paces (road only). When present, the easy
            portion uses the EF zone and the finish block uses the MPR zone.

    Returns:
        Dictionary with keys:
            - target_km (float): Target long run distance in kilometers.
            - target_duration_seconds (int): Estimated duration in seconds.
            - progression_note (str): Human-readable note about progression.

        For road runs the dict additionally carries:
            - variant (str): ``progressive_easy`` | ``marathon_pace_finish`` |
              ``fast_finish`` | ``taper_quality`` | ``recovery_easy``.
            - marathon_pace_block_km (float): km run at marathon pace (0 if none).
            - fast_finish (bool): whether the last km are run faster than MP.
            - hr_zone (str): HR zone bounding the easy portion (``"Z2"``).
            - easy_pace (str | None): EF pace label from the PaceSet.
            - marathon_pace (str | None): MPR pace label from the PaceSet.

    Raises:
        ValueError: If week_number or total_weeks are invalid.
    """
    if week_number < 1 or week_number > total_weeks:
        raise ValueError(f"week_number must be between 1 and {total_weeks}")

    if total_weeks < 1:
        raise ValueError("total_weeks must be at least 1")

    is_road = discipline == "road"

    # Determine starting long run distance based on experience if not provided
    if current_long_run_km <= 0:
        starting_lr = _get_starting_long_run(experience)
    else:
        starting_lr = current_long_run_km

    # Get phase-specific cap as percentage of race distance, then the discipline
    # absolute cap (road marathons never exceed 35 km).
    phase_cap_percent = _get_phase_cap_percent(phase)
    phase_cap_km = race_distance_km * (phase_cap_percent / 100.0)
    absolute_cap_km = _ROAD_ABSOLUTE_CAP_KM if is_road else _TRAIL_ABSOLUTE_CAP_KM
    phase_cap_km = min(phase_cap_km, absolute_cap_km)

    # Calculate progression within phase
    progression_rate = _get_progression_rate(experience)

    if is_recovery_week:
        # Recovery weeks: reduce by 40% from starting point
        target_km = starting_lr * 0.6
        note = "Recovery week: 40% reduction"
    else:
        # Progressive build: add percentage per week
        weekly_increase = starting_lr * (progression_rate / 100.0)

        target_km = starting_lr + (weekly_increase * (week_number - 1))
        note = f"Progressive build: {progression_rate}% per week"

    # Apply phase cap
    target_km = min(target_km, phase_cap_km)

    if is_road:
        return _build_road_long_run(
            target_km=target_km,
            week_number=week_number,
            phase=phase,
            is_recovery_week=is_recovery_week,
            pace_set=pace_set,
            note=note,
        )

    # Trail: single easy pace by experience level.
    pace_min_per_km = _get_trail_pace(experience)
    target_duration_seconds = int(target_km * pace_min_per_km * 60)

    return {
        "target_km": round(target_km, 1),
        "target_duration_seconds": target_duration_seconds,
        "progression_note": note,
    }


def _build_road_long_run(
    target_km: float,
    week_number: int,
    phase: PlanPhase,
    is_recovery_week: bool,
    pace_set: "Optional[PaceSet]",
    note: str,
) -> dict:
    """Assemble a road-marathon long run with phase-appropriate variants.

    Variants (spec §6):
        - base / development: progressive easy run, all EF, HR Z2.
        - specific: marathon-pace finish block (last ~10-12 km at MPR), with an
          occasional fast finish.
        - taper: reduced volume but intensity KEPT — a short MPR block remains.
        - recovery weeks: easy only, no marathon-pace block.

    Args:
        target_km: Capped target distance for the week.
        week_number: Current week number (used to vary the fast-finish cadence).
        phase: Training phase.
        is_recovery_week: Whether this week is a recovery week.
        pace_set: Optional VMA-derived paces for EF/MPR labels and duration.
        note: Progression note carried through from the caller.

    Returns:
        The long-run dict enriched with road variant metadata.
    """
    mp_block_km = 0.0
    fast_finish = False

    if is_recovery_week:
        variant = "recovery_easy"
    elif phase == PlanPhase.specific:
        variant = "marathon_pace_finish"
        mp_block_km = round(
            min(_ROAD_MP_BLOCK_MAX_KM, target_km * _ROAD_MP_BLOCK_FRACTION), 1
        )
        # Alternate a fast-finish twist for variety (deterministic by week).
        fast_finish = week_number % 2 == 0
        if fast_finish:
            variant = "fast_finish"
    elif phase == PlanPhase.taper:
        # Cut volume, keep intensity: retain a short marathon-pace block.
        variant = "taper_quality"
        # The build note is meaningless in the taper (volume goes down, not up).
        note = "Taper: reduced volume, intensity kept"
        mp_block_km = round(
            min(_ROAD_TAPER_MP_BLOCK_MAX_KM, target_km * _ROAD_TAPER_MP_BLOCK_FRACTION),
            1,
        )
    else:  # base, development
        variant = "progressive_easy"

    easy_km = max(target_km - mp_block_km, 0.0)

    # Duration: easy portion at EF, marathon-pace block at MPR.
    if pace_set is not None:
        ef_sec = pace_set.zones["EF"].sec_per_km_slow
        mpr_sec = pace_set.zones["MPR"].sec_per_km_fast
        easy_pace = pace_set.zones["EF"].label
        marathon_pace = pace_set.zones["MPR"].label
    else:
        ef_sec = int(_ROAD_DEFAULT_EASY_PACE_MIN * 60)
        mpr_sec = ef_sec
        easy_pace = None
        marathon_pace = None

    target_duration_seconds = int(easy_km * ef_sec + mp_block_km * mpr_sec)

    return {
        "target_km": round(target_km, 1),
        "target_duration_seconds": target_duration_seconds,
        "progression_note": note,
        "variant": variant,
        "marathon_pace_block_km": mp_block_km,
        "easy_km": round(easy_km, 1),
        "fast_finish": fast_finish,
        "hr_zone": "Z2",
        "easy_pace": easy_pace,
        "marathon_pace": marathon_pace,
        # Per-km seconds for each portion — lets the week builder split the run
        # into a Z2 easy block + a Z3 marathon-pace finish block (durations).
        "easy_pace_sec": ef_sec,
        "marathon_pace_sec": mpr_sec,
    }


def scale_long_run_spec(spec: dict, scale: float) -> dict:
    """Return a copy of a long-run spec with its volume scaled by ``scale``.

    Distance and duration shrink together so the rendered pace stays correct.
    This backs the plan generator's weekly TSS-progression guard, which used to
    trim only the duration and leave the distance (and thus the implied pace)
    incoherent — a 21 km run rendered as 1h12 (3:24/km, impossible). Per-km pace
    fields and the remaining metadata are preserved.

    Args:
        spec: A ``calculate_long_run`` output dict.
        scale: Multiplier; values >= 1.0 return the spec unchanged.

    Returns:
        A new spec dict with ``target_km`` and ``target_duration_seconds`` scaled
        (plus ``easy_km`` / ``marathon_pace_block_km`` for road runs). Durations
        are recomputed from the scaled distances and the preserved paces so the
        blocks the week builder derives stay self-consistent.
    """
    if scale >= 1.0:
        return spec

    scaled = dict(spec)
    scaled["target_km"] = round(spec["target_km"] * scale, 1)
    for key in ("easy_km", "marathon_pace_block_km"):
        if spec.get(key):
            scaled[key] = round(spec[key] * scale, 1)

    # Recompute duration from the scaled distances × preserved paces so
    # distance ÷ duration keeps yielding the right pace. Trail specs carry no
    # per-km pace, so scale their duration directly.
    ef_sec = spec.get("easy_pace_sec")
    if ef_sec is not None:
        mpr_sec = spec.get("marathon_pace_sec") or ef_sec
        scaled["target_duration_seconds"] = int(
            scaled.get("easy_km", 0) * ef_sec
            + scaled.get("marathon_pace_block_km", 0) * mpr_sec
        )
    else:
        scaled["target_duration_seconds"] = int(spec["target_duration_seconds"] * scale)

    return scaled


def _get_starting_long_run(experience: ExperienceLevel) -> float:
    """Get default starting long run distance by experience level.

    Args:
        experience: Athlete experience level.

    Returns:
        Starting long run distance in kilometers.
    """
    defaults = {
        ExperienceLevel.beginner: 10.0,
        ExperienceLevel.intermediate: 15.0,
        ExperienceLevel.advanced: 20.0,
        ExperienceLevel.expert: 25.0,
    }
    return defaults[experience]


def _get_progression_rate(experience: ExperienceLevel) -> float:
    """Get weekly progression rate by experience level.

    Args:
        experience: Athlete experience level.

    Returns:
        Weekly progression rate as a percentage (10-15%).
    """
    rates = {
        ExperienceLevel.beginner: 10.0,
        ExperienceLevel.intermediate: 12.0,
        ExperienceLevel.advanced: 13.0,
        ExperienceLevel.expert: 15.0,
    }
    return rates[experience]


def _get_phase_cap_percent(phase: PlanPhase) -> float:
    """Get phase-specific cap as percentage of race distance.

    Args:
        phase: Training periodization phase.

    Returns:
        Cap as a percentage of race distance.
    """
    caps = {
        PlanPhase.base: 30.0,
        PlanPhase.development: 50.0,
        PlanPhase.specific: 70.0,
        PlanPhase.taper: 40.0,
    }
    return caps[phase]


def _get_trail_pace(experience: ExperienceLevel) -> float:
    """Get average trail running pace by experience level.

    Args:
        experience: Athlete experience level.

    Returns:
        Pace in minutes per kilometer.
    """
    paces = {
        ExperienceLevel.beginner: 8.0,
        ExperienceLevel.intermediate: 7.0,
        ExperienceLevel.advanced: 6.0,
        ExperienceLevel.expert: 5.5,
    }
    return paces[experience]
