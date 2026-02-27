"""Progressive long run calculator with phase-based caps for trail training."""

from .models import ExperienceLevel, PlanPhase


def calculate_long_run(
    week_number: int,
    total_weeks: int,
    phase: PlanPhase,
    is_recovery_week: bool,
    experience: ExperienceLevel,
    race_distance_km: float,
    current_long_run_km: float,
) -> dict:
    """Calculate target long run for a given week.

    Uses progressive overload adapted to experience level and training phase,
    with phase-specific caps as percentages of race distance.

    Args:
        week_number: Current week number in training plan (1-indexed).
        total_weeks: Total number of weeks in the training plan.
        phase: Current training phase (base, development, specific, taper).
        is_recovery_week: Whether this is a recovery week.
        experience: Athlete experience level (beginner, intermediate, advanced, expert).
        race_distance_km: Target race distance in kilometers.
        current_long_run_km: Current long run distance in kilometers (from fitness snapshot).

    Returns:
        Dictionary with keys:
            - target_km (float): Target long run distance in kilometers.
            - target_duration_seconds (int): Estimated duration in seconds.
            - progression_note (str): Human-readable note about progression.

    Raises:
        ValueError: If week_number or total_weeks are invalid.
    """
    if week_number < 1 or week_number > total_weeks:
        raise ValueError(f"week_number must be between 1 and {total_weeks}")

    if total_weeks < 1:
        raise ValueError("total_weeks must be at least 1")

    # Determine starting long run distance based on experience if not provided
    if current_long_run_km <= 0:
        starting_lr = _get_starting_long_run(experience)
    else:
        starting_lr = current_long_run_km

    # Get phase-specific cap as percentage of race distance
    phase_cap_percent = _get_phase_cap_percent(phase)
    phase_cap_km = race_distance_km * (phase_cap_percent / 100.0)
    phase_cap_km = min(phase_cap_km, 80.0)  # Absolute cap of 80km

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

    # Estimate duration using pace by experience level
    pace_min_per_km = _get_trail_pace(experience)
    target_duration_seconds = int(target_km * pace_min_per_km * 60)

    return {
        "target_km": round(target_km, 1),
        "target_duration_seconds": target_duration_seconds,
        "progression_note": note,
    }


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
