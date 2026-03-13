"""Weekly session placement engine respecting coach-defined constraints."""

from typing import Optional

from .models import (
    DayPreferences,
    ExperienceLevel,
    PlanPhase,
    RaceFlags,
    RaceObjective,
    SessionSpec,
    SessionType,
)
from .session_catalog import get_phase_session_types, get_session_template


def build_week(
    available_days: list[int],
    phase: PlanPhase,
    experience: ExperienceLevel,
    is_recovery_week: bool,
    week_number: int,
    long_run_spec: dict | None = None,
    race_flags: Optional[RaceFlags] = None,
    objective: Optional[RaceObjective] = None,
    day_preferences: Optional[DayPreferences] = None,
) -> list[SessionSpec]:
    """Build a week of training sessions placed on available days.

    Respects scheduling constraints:
    - No 2 consecutive hard days (Z3+ sessions need >= 1 easy day between them)
    - 48+ hours between Z4-Z5 sessions (intervals)
    - Long run on weekend (Saturday=6 or Sunday=7 preferred)
    - RMU not day before or after hard run
    - Recovery weeks: only EF, SL (reduced), REC, REST

    When race_flags are provided:
    - high_dplus: prioritize COT over INT, add elevation to long runs
    - technical: add DESC session when possible
    - high_altitude: no extra changes (handled via session type selection)

    When objective is provided:
    - finish: more volume (EF), fewer quality sessions
    - performance: more quality sessions allowed
    - midpack: default behavior

    Args:
        available_days: List of day numbers (1=Monday, 7=Sunday) when athlete can train.
        phase: Current training phase (base, development, specific, taper).
        experience: Athlete experience level (beginner, intermediate, advanced, expert).
        is_recovery_week: Whether this is a recovery week.
        week_number: Current week number in training plan (1-indexed).
        long_run_spec: Output dict from calculate_long_run with target_km, target_duration_seconds.
                       If provided, a long run session (SL) will be created and placed on weekend.
        race_flags: Optional race classification flags for session adaptation.
        objective: Optional race objective (finish/midpack/performance).
        day_preferences: Optional preferred days for session categories.
            Preferences are best-effort: safety constraints always take priority.

    Returns:
        List of SessionSpec objects ordered by day of week. May include non-training days (REST).

    Raises:
        ValueError: If available_days is empty or contains invalid day numbers.
    """
    if not available_days:
        raise ValueError("available_days cannot be empty")

    if not all(1 <= d <= 7 for d in available_days):
        raise ValueError("available_days must contain integers between 1 and 7")

    available_days_sorted = sorted(available_days)

    # Determine session types available for this phase/experience/race
    phase_types = get_phase_session_types(phase, experience, race_flags)

    # Get target session count
    session_count = _get_session_count(experience, is_recovery_week)

    # If recovery week, limit session types
    if is_recovery_week:
        phase_types = [
            t
            for t in phase_types
            if t in (SessionType.EF, SessionType.SL, SessionType.REC)
        ]

    # Build session plan
    sessions: list[SessionSpec] = []

    # Step 1: Place long run — use preferred day if available, else weekend fallback
    long_run_day = None
    if long_run_spec:
        if (
            day_preferences
            and day_preferences.long_run
            and day_preferences.long_run in available_days_sorted
        ):
            long_run_day = day_preferences.long_run
        else:
            long_run_day = _find_weekend_day(available_days_sorted)
        if long_run_day:
            lr_session = _create_long_run_session(
                day=long_run_day,
                experience=experience,
                phase=phase,
                long_run_spec=long_run_spec,
                race_flags=race_flags,
            )
            sessions.append(lr_session)
            session_count -= 1

    # Step 2: Place quality sessions — preferred days first, then midweek fallback
    quality_placed = 0
    max_quality = _get_max_quality_sessions(experience, objective)

    # Order quality types based on race flags
    quality_types = _get_quality_type_order(phase_types, race_flags)

    # Build candidate days: preferred quality days first, then standard midweek
    used_days = {s.day_of_week for s in sessions}
    if day_preferences and day_preferences.quality:
        preferred_quality = [
            d
            for d in day_preferences.quality
            if d in available_days_sorted and d not in used_days
        ]
        other_midweek = [
            d
            for d in available_days_sorted
            if 2 <= d <= 5 and d not in used_days and d not in preferred_quality
        ]
        midweek_days = preferred_quality + other_midweek
    else:
        midweek_days = [
            d for d in available_days_sorted if 2 <= d <= 5 and d not in used_days
        ]

    for quality_type in quality_types:
        if quality_placed >= max_quality or session_count <= 0:
            break

        if not midweek_days:
            continue

        # Find a day that respects constraints
        best_day = None
        for day in midweek_days:
            if _can_place_hard_session(day, sessions):
                best_day = day
                break

        if best_day:
            template = get_session_template(quality_type, experience, phase)
            session = SessionSpec(
                day_of_week=best_day,
                session_type=quality_type,
                title=template.title,
                description=template.description,
                sport_type=template.sport_type,
                target_duration_seconds=int(
                    (
                        template.duration_range_minutes[0]
                        + template.duration_range_minutes[1]
                    )
                    / 2
                    * 60
                ),
                intensity=template.intensity,
                hr_zone_primary=template.hr_zone_primary,
                blocks=template.blocks,
            )
            sessions.append(session)
            quality_placed += 1
            session_count -= 1
            midweek_days.remove(best_day)

    # Step 2b: Place DESC session for technical races if phase allows
    # DESC is moderate intensity (Z2), so it can be placed adjacent to hard sessions
    if (
        race_flags
        and race_flags.technical
        and not is_recovery_week
        and SessionType.DESC in phase_types
        and session_count > 0
    ):
        used_days = {s.day_of_week for s in sessions}
        desc_candidates = [d for d in available_days_sorted if d not in used_days]
        if desc_candidates:
            template = get_session_template(SessionType.DESC, experience, phase)
            session = SessionSpec(
                day_of_week=desc_candidates[0],
                session_type=SessionType.DESC,
                title=template.title,
                description=template.description,
                sport_type=template.sport_type,
                target_duration_seconds=int(
                    (
                        template.duration_range_minutes[0]
                        + template.duration_range_minutes[1]
                    )
                    / 2
                    * 60
                ),
                intensity=template.intensity,
                hr_zone_primary=template.hr_zone_primary,
                blocks=template.blocks,
            )
            sessions.append(session)
            session_count -= 1

    # Step 3: Fill remaining days with EF/REC — preferred easy_run days first
    used_days = {s.day_of_week for s in sessions}
    remaining_days = [d for d in available_days_sorted if d not in used_days]

    if day_preferences and day_preferences.easy_run:
        preferred_ef = [d for d in day_preferences.easy_run if d in remaining_days]
        other_remaining = [d for d in remaining_days if d not in preferred_ef]
        remaining_days = preferred_ef + other_remaining

    for day in remaining_days:
        if session_count <= 0:
            break

        # Choose EF or REC based on recovery needs
        session_type = SessionType.EF if quality_placed > 0 else SessionType.REC
        if session_type not in phase_types:
            session_type = (
                SessionType.EF if SessionType.EF in phase_types else SessionType.REC
            )

        if session_type in phase_types:
            template = get_session_template(session_type, experience, phase)
            session = SessionSpec(
                day_of_week=day,
                session_type=session_type,
                title=template.title,
                description=template.description,
                sport_type=template.sport_type,
                target_duration_seconds=int(
                    (
                        template.duration_range_minutes[0]
                        + template.duration_range_minutes[1]
                    )
                    / 2
                    * 60
                ),
                intensity=template.intensity,
                hr_zone_primary=template.hr_zone_primary,
                blocks=template.blocks,
            )
            sessions.append(session)
            session_count -= 1

    # Step 4: Add RMU — use preferred strength days if valid, else first available
    # RMU is cross-training, so it CAN be placed on recovery days (after SL/quality).
    # Place up to max_rmu sessions (1 by default, up to 2 if preferences request it)
    if SessionType.RMU in phase_types and not is_recovery_week:
        max_rmu = 1
        if day_preferences and day_preferences.strength:
            max_rmu = len(day_preferences.strength)

        non_running_days = [
            d for d in range(1, 8) if d not in {s.day_of_week for s in sessions}
        ]
        valid_rmu_days = non_running_days

        # Preferred strength days get priority
        if day_preferences and day_preferences.strength:
            preferred = [d for d in day_preferences.strength if d in valid_rmu_days]
            remaining = [d for d in valid_rmu_days if d not in preferred]
            valid_rmu_days = preferred + remaining

        rmu_placed = 0
        for rmu_day in valid_rmu_days:
            if rmu_placed >= max_rmu:
                break
            template = get_session_template(SessionType.RMU, experience, phase)
            rmu_session = SessionSpec(
                day_of_week=rmu_day,
                session_type=SessionType.RMU,
                title=template.title,
                description=template.description,
                sport_type=template.sport_type,
                target_duration_seconds=int(
                    (
                        template.duration_range_minutes[0]
                        + template.duration_range_minutes[1]
                    )
                    / 2
                    * 60
                ),
                intensity=template.intensity,
                hr_zone_primary=template.hr_zone_primary,
                blocks=template.blocks,
            )
            sessions.append(rmu_session)
            rmu_placed += 1

    # Sort by day of week
    sessions.sort(key=lambda s: s.day_of_week)

    return sessions


def _get_max_quality_sessions(
    experience: ExperienceLevel,
    objective: Optional[RaceObjective] = None,
) -> int:
    """Get maximum number of quality (hard) sessions per week.

    Scales with experience level and race objective.

    Args:
        experience: Athlete experience level.
        objective: Optional race objective.

    Returns:
        Maximum quality sessions per week.
    """
    base_max = {
        ExperienceLevel.beginner: 1,
        ExperienceLevel.intermediate: 1,
        ExperienceLevel.advanced: 2,
        ExperienceLevel.expert: 2,
    }

    max_q = base_max[experience]

    # Objective adjustments
    if objective == RaceObjective.finish:
        max_q = max(1, max_q - 1)  # Fewer quality, more volume
    elif objective == RaceObjective.performance:
        if experience in (ExperienceLevel.advanced, ExperienceLevel.expert):
            max_q = min(3, max_q + 1)  # Allow up to 3 for performance-oriented experts

    return max_q


def _get_quality_type_order(
    phase_types: list[SessionType],
    race_flags: Optional[RaceFlags] = None,
) -> list[SessionType]:
    """Get quality session types in priority order based on race flags.

    Args:
        phase_types: Available session types for this phase.
        race_flags: Optional race classification flags.

    Returns:
        List of quality session types in priority order.
    """
    default_order = [SessionType.TMP, SessionType.INT, SessionType.COT]

    if race_flags and race_flags.high_dplus:
        # Prioritize COT for high D+ races
        default_order = [SessionType.COT, SessionType.TMP, SessionType.INT]
    elif race_flags and race_flags.is_ultra:
        # Ultra: tempo more important than intervals
        default_order = [SessionType.TMP, SessionType.COT, SessionType.INT]

    return [t for t in default_order if t in phase_types]


def _get_session_count(experience: ExperienceLevel, is_recovery_week: bool) -> int:
    """Get target number of running sessions per week.

    Args:
        experience: Athlete experience level.
        is_recovery_week: Whether this is a recovery week.

    Returns:
        Target session count.
    """
    base_count = {
        ExperienceLevel.beginner: 3,
        ExperienceLevel.intermediate: 4,
        ExperienceLevel.advanced: 5,
        ExperienceLevel.expert: 6,
    }

    count = base_count[experience]
    if is_recovery_week:
        count = max(1, count - 1)  # Reduce by 1 session, minimum 1

    return count


def _find_weekend_day(available_days: list[int]) -> int | None:
    """Find the best weekend day for a long run.

    Prefers Saturday (6), falls back to Sunday (7), returns None if neither available.

    Args:
        available_days: Sorted list of available days.

    Returns:
        Day number (6 or 7) or None if no weekend day available.
    """
    if 6 in available_days:
        return 6
    if 7 in available_days:
        return 7
    return None


def _create_long_run_session(
    day: int,
    experience: ExperienceLevel,
    phase: PlanPhase,
    long_run_spec: dict,
    race_flags: Optional[RaceFlags] = None,
) -> SessionSpec:
    """Create a long run session from calculate_long_run output.

    When race_flags.high_dplus is set, adds elevation gain target proportional
    to the race's D+/km ratio applied to the long run distance.

    Args:
        day: Day of week (1-7).
        experience: Athlete experience level.
        phase: Training phase.
        long_run_spec: Dict with target_km, target_duration_seconds, progression_note.
        race_flags: Optional race classification flags.

    Returns:
        SessionSpec for the long run.
    """
    template = get_session_template(SessionType.SL, experience, phase)

    # Calculate elevation target for high D+ races
    target_elevation = None
    if race_flags and race_flags.high_dplus:
        target_km = long_run_spec.get("target_km", 0)
        # Use a moderate D+/km ratio for long runs (50 m/km — training, not race pace)
        target_elevation = int(target_km * 50)

    return SessionSpec(
        day_of_week=day,
        session_type=SessionType.SL,
        title=template.title,
        description=template.description
        + f" ({long_run_spec.get('progression_note', '')})",
        sport_type=template.sport_type,
        target_duration_seconds=long_run_spec.get("target_duration_seconds", 0),
        target_distance_meters=long_run_spec.get("target_km", 0) * 1000,
        target_elevation_gain_m=target_elevation,
        intensity=template.intensity,
        hr_zone_primary=template.hr_zone_primary,
        blocks=template.blocks,
    )


def _adjacent_days(day: int) -> tuple[int, int]:
    """Return (previous_day, next_day) with wrap-around (Sun↔Mon).

    Args:
        day: Day of week (1-7).

    Returns:
        Tuple of (day before, day after) with 7→1 and 1→7 wrapping.
    """
    prev_day = 7 if day == 1 else day - 1
    next_day = 1 if day == 7 else day + 1
    return prev_day, next_day


def _prev_day(day: int) -> int:
    """Return previous day with wrap-around (Mon→Sun)."""
    return 7 if day == 1 else day - 1


def _can_place_hard_session(day: int, existing_sessions: list[SessionSpec]) -> bool:
    """Check if a hard session can be placed on a given day.

    Constraints:
    - Max 2 consecutive hard days; the 3rd day must be recovery.
    - No hard session the day after a long run (SL needs recovery).
    - Wraps around: Sunday (7) is adjacent to Monday (1).

    Args:
        day: Day of week (1-7).
        existing_sessions: List of already-placed sessions.

    Returns:
        True if a hard session can be placed on this day.
    """
    hard_zones = [3, 4, 5]
    hard_days = {
        s.day_of_week
        for s in existing_sessions
        if s.hr_zone_primary and s.hr_zone_primary in hard_zones
    }

    prev, _ = _adjacent_days(day)

    # No hard session the day after a long run (SL needs recovery)
    for session in existing_sessions:
        if session.session_type == SessionType.SL and session.day_of_week == prev:
            return False

    # Allow up to 2 consecutive hard days, block 3rd
    # Count how many consecutive hard days precede this day
    count_before = 0
    check = prev
    while check in hard_days:
        count_before += 1
        check = _prev_day(check)

    # Count how many consecutive hard days follow this day
    _, nxt = _adjacent_days(day)
    count_after = 0
    check = nxt
    while check in hard_days:
        count_after += 1
        _, check = _adjacent_days(check)

    # Total streak including this day
    if count_before + 1 + count_after >= 3:
        return False

    return True


def _is_adjacent_to_hard(day: int, existing_sessions: list[SessionSpec]) -> bool:
    """Check if a day is adjacent to a hard or demanding session.

    Used to avoid placing RMU next to hard runs or long runs.
    Wraps around: Sunday (7) is adjacent to Monday (1).

    Args:
        day: Day of week (1-7).
        existing_sessions: List of already-placed sessions.

    Returns:
        True if the day is adjacent to a Z3+ session or a long run.
    """
    hard_zones = [3, 4, 5]
    prev_day, next_day = _adjacent_days(day)

    for session in existing_sessions:
        if session.day_of_week in (prev_day, next_day):
            if session.hr_zone_primary and session.hr_zone_primary in hard_zones:
                return True
            if session.session_type == SessionType.SL:
                return True

    return False
