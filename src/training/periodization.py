"""Periodization engine for training plan phases with load/unload cycles."""

from .models import ExperienceLevel, PlanPhase, RaceCategory, WeekSpec


def build_periodization(
    total_weeks: int,
    experience: ExperienceLevel,
    race_category: RaceCategory,
) -> list[WeekSpec]:
    """Build the full periodization plan.

    Splits total weeks into 4 phases (base, development, specific, taper) with
    appropriate load/unload cycles based on athlete experience level.

    Args:
        total_weeks: Total number of weeks in the plan.
        experience: Athlete experience level.
        race_category: Race category for phase emphasis.

    Returns:
        List of WeekSpec for each week, in order.
    """
    if total_weeks < 6:
        raise ValueError("Plan must have at least 6 weeks")
    if total_weeks > 30:
        raise ValueError("Plan must have at most 30 weeks")

    # Calculate phase durations
    phases_weeks = _calculate_phase_durations(total_weeks, race_category)
    base_weeks = phases_weeks["base"]
    dev_weeks = phases_weeks["development"]
    specific_weeks = phases_weeks["specific"]
    taper_weeks = phases_weeks["taper"]

    # Get recovery week pattern based on experience
    recovery_pattern = _get_recovery_pattern(experience)

    weeks = []
    week_number = 1

    # Base phase
    for i in range(base_weeks):
        is_recovery = (i + 1) % recovery_pattern == 0
        weeks.append(
            WeekSpec(week_number=week_number, phase=PlanPhase.base, is_recovery_week=is_recovery)
        )
        week_number += 1

    # Development phase
    for i in range(dev_weeks):
        is_recovery = (i + 1) % recovery_pattern == 0
        weeks.append(
            WeekSpec(
                week_number=week_number, phase=PlanPhase.development, is_recovery_week=is_recovery
            )
        )
        week_number += 1

    # Specific phase
    for i in range(specific_weeks):
        is_recovery = (i + 1) % recovery_pattern == 0
        weeks.append(
            WeekSpec(
                week_number=week_number, phase=PlanPhase.specific, is_recovery_week=is_recovery
            )
        )
        week_number += 1

    # Taper phase (no recovery weeks, already reduced load)
    for i in range(taper_weeks):
        weeks.append(
            WeekSpec(week_number=week_number, phase=PlanPhase.taper, is_recovery_week=False)
        )
        week_number += 1

    # Ensure last week is marked as recovery (final taper before race)
    if weeks:
        weeks[-1].is_recovery_week = True

    return weeks


def _calculate_phase_durations(total_weeks: int, race_category: RaceCategory) -> dict[str, int]:
    """Calculate phase durations based on total weeks and race category.

    Base percentages: base 30%, development 30%, specific 25%, taper 15%.
    For ultra categories: base 25%, development 30%, specific 30%, taper 15%.

    Args:
        total_weeks: Total number of weeks in the plan.
        race_category: Race category for emphasis adjustment.

    Returns:
        Dict with phase names as keys and week counts as values.
    """
    is_ultra = race_category in (RaceCategory.ultra, RaceCategory.ultra_longue)

    if is_ultra:
        base_pct = 0.25
        dev_pct = 0.30
        specific_pct = 0.30
        taper_pct = 0.15
    else:
        base_pct = 0.30
        dev_pct = 0.30
        specific_pct = 0.25
        taper_pct = 0.15

    # Calculate weeks for each phase, starting with percentages
    base_weeks = round(total_weeks * base_pct)
    dev_weeks = round(total_weeks * dev_pct)
    specific_weeks = round(total_weeks * specific_pct)
    taper_weeks = round(total_weeks * taper_pct)

    # Ensure taper is between 1 and 3 weeks
    taper_weeks = max(1, min(3, taper_weeks))

    # Adjust to match total
    assigned = base_weeks + dev_weeks + specific_weeks + taper_weeks
    diff = total_weeks - assigned

    if diff != 0:
        # Distribute difference to largest phases (prioritize base and dev)
        if diff > 0:
            for _ in range(diff):
                if dev_weeks >= base_weeks:
                    dev_weeks += 1
                else:
                    base_weeks += 1
        else:
            # Remove from specific phase first, then base
            for _ in range(-diff):
                if specific_weeks > 1:
                    specific_weeks -= 1
                elif base_weeks > 1:
                    base_weeks -= 1
                else:
                    dev_weeks -= 1

    return {
        "base": base_weeks,
        "development": dev_weeks,
        "specific": specific_weeks,
        "taper": taper_weeks,
    }


def _get_recovery_pattern(experience: ExperienceLevel) -> int:
    """Get recovery week frequency (cycle length) based on experience.

    Beginner: every 2 weeks (2:1 pattern)
    Intermediate: every 3 weeks (3:1 pattern)
    Advanced: every 3 weeks (3:1 pattern)
    Expert: every 4 weeks (4:1 pattern)

    Args:
        experience: Athlete experience level.

    Returns:
        Cycle length (recovery week appears every N weeks).
    """
    patterns = {
        ExperienceLevel.beginner: 2,
        ExperienceLevel.intermediate: 3,
        ExperienceLevel.advanced: 3,
        ExperienceLevel.expert: 4,
    }
    return patterns[experience]


def get_phase_volume_factor(phase: PlanPhase, is_recovery_week: bool) -> float:
    """Return volume multiplier for a phase/recovery combination.

    Base phase: 0.7x volume
    Development phase: 0.85x volume
    Specific phase: 1.0x volume (full)
    Taper phase: 0.5x volume

    Recovery weeks multiply the phase factor by 0.6.

    Args:
        phase: Training phase.
        is_recovery_week: Whether this is a recovery week.

    Returns:
        Volume multiplier as a float.
    """
    phase_factors = {
        PlanPhase.base: 0.7,
        PlanPhase.development: 0.85,
        PlanPhase.specific: 1.0,
        PlanPhase.taper: 0.5,
    }

    factor = phase_factors[phase]

    if is_recovery_week:
        factor *= 0.6

    return factor
