"""Training load (TSS) calculator for trail running.

Calculates Training Stress Score based on session type, duration,
and elevation gain, with validation against weekly limits.
"""

from .models import ExperienceLevel, SessionType

# Intensity factors by session type
INTENSITY_FACTORS = {
    SessionType.REST: 0,
    SessionType.REC: 30,
    SessionType.EF: 50,
    SessionType.SL: 55,
    SessionType.MPR: 62,  # marathon pace, between SL (55) and TMP (70)
    SessionType.RMU: 45,
    SessionType.DESC: 40,
    SessionType.TMP: 70,
    SessionType.COT: 75,
    SessionType.INT: 85,
}

# Weekly TSS limits by experience level
WEEKLY_TSS_LIMITS = {
    ExperienceLevel.beginner: {"min": 150, "max": 350, "peak": 400},
    ExperienceLevel.intermediate: {"min": 250, "max": 500, "peak": 600},
    ExperienceLevel.advanced: {"min": 350, "max": 700, "peak": 850},
    ExperienceLevel.expert: {"min": 450, "max": 900, "peak": 1100},
}


def calculate_session_tss(
    session_type: SessionType,
    duration_seconds: int,
    elevation_gain_m: int = 0,
) -> float:
    """Calculate TSS for a single session.

    TSS = (duration_seconds / 3600) × intensity_factor × elevation_factor

    Where elevation_factor = 1.0 + (elevation_gain_m / 1000) × 0.15

    Args:
        session_type: Type of training session.
        duration_seconds: Session duration in seconds.
        elevation_gain_m: Total elevation gain in meters. Defaults to 0.

    Returns:
        Training Stress Score as a float.
    """
    intensity_factor = INTENSITY_FACTORS[session_type]

    # REST sessions have 0 TSS regardless of duration/elevation
    if intensity_factor == 0:
        return 0.0

    # Elevation factor calculation
    elevation_factor = 1.0 + (elevation_gain_m / 1000) * 0.15

    # TSS calculation
    duration_hours = duration_seconds / 3600
    tss = duration_hours * intensity_factor * elevation_factor

    return round(tss, 1)


def get_weekly_tss_limits(experience: ExperienceLevel) -> dict[str, int]:
    """Return min/max/peak weekly TSS for a given experience level.

    Args:
        experience: Athlete experience level.

    Returns:
        Dictionary with 'min', 'max', and 'peak' keys.
    """
    return WEEKLY_TSS_LIMITS[experience]


def validate_weekly_progression(
    current_week_tss: float,
    previous_week_tss: float,
    max_increase_pct: float = 15.0,
) -> tuple[bool, float]:
    """Check the +15% rule: weekly TSS should not increase more than 15%.

    Ensures safe training progression by limiting week-to-week increases.

    Args:
        current_week_tss: Target TSS for the current week.
        previous_week_tss: Actual TSS from the previous week.
        max_increase_pct: Maximum allowed increase percentage. Defaults to 15.0.

    Returns:
        Tuple of (is_valid, suggested_max_tss).
        - is_valid: True if current_week_tss respects the rule.
        - suggested_max_tss: Maximum TSS allowed for current week.
    """
    if previous_week_tss == 0:
        return (True, current_week_tss)

    suggested_max = previous_week_tss * (1.0 + max_increase_pct / 100.0)
    is_valid = current_week_tss <= suggested_max

    return (is_valid, round(suggested_max, 1))


def calculate_recovery_week_tss(
    normal_week_tss: float,
    reduction_pct: float = 40.0,
) -> float:
    """Calculate target TSS for a recovery/unload week.

    Recovery weeks typically run at 60% of normal (40% reduction).

    Args:
        normal_week_tss: Target TSS for a typical training week.
        reduction_pct: Percentage reduction for recovery. Defaults to 40.0 (60% of normal).

    Returns:
        Target TSS for the recovery week.
    """
    recovery_multiplier = 1.0 - (reduction_pct / 100.0)
    recovery_tss = normal_week_tss * recovery_multiplier

    return round(recovery_tss, 1)
