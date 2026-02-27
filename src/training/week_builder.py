"""Weekly session placement engine respecting coach-defined constraints."""

from .models import (
    ExperienceLevel,
    PlanPhase,
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
) -> list[SessionSpec]:
    """Build a week of training sessions placed on available days.

    Respects scheduling constraints:
    - No 2 consecutive hard days (Z3+ sessions need >= 1 easy day between them)
    - 48+ hours between Z4-Z5 sessions (intervals)
    - Long run on weekend (Saturday=6 or Sunday=7 preferred)
    - RMU not day before or after hard run
    - Recovery weeks: only EF, SL (reduced), REC, REST

    Args:
        available_days: List of day numbers (1=Monday, 7=Sunday) when athlete can train.
        phase: Current training phase (base, development, specific, taper).
        experience: Athlete experience level (beginner, intermediate, advanced, expert).
        is_recovery_week: Whether this is a recovery week.
        week_number: Current week number in training plan (1-indexed).
        long_run_spec: Output dict from calculate_long_run with target_km, target_duration_seconds.
                       If provided, a long run session (SL) will be created and placed on weekend.

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

    # Determine session types available for this phase/experience
    phase_types = get_phase_session_types(phase, experience)

    # Get target session count
    session_count = _get_session_count(experience, is_recovery_week)

    # If recovery week, limit session types
    if is_recovery_week:
        phase_types = [t for t in phase_types if t in (SessionType.EF, SessionType.SL, SessionType.REC)]

    # Build session plan
    sessions: list[SessionSpec] = []

    # Step 1: Place long run on weekend if provided
    long_run_day = None
    if long_run_spec:
        long_run_day = _find_weekend_day(available_days_sorted)
        if long_run_day:
            lr_session = _create_long_run_session(
                day=long_run_day,
                experience=experience,
                phase=phase,
                long_run_spec=long_run_spec,
            )
            sessions.append(lr_session)
            session_count -= 1

    # Step 2: Place intervals/tempo on midweek days (prefer Tue/Wed/Thu)
    quality_placed = 0
    quality_types = [SessionType.TMP, SessionType.INT, SessionType.COT]
    quality_types = [t for t in quality_types if t in phase_types]

    midweek_days = [d for d in available_days_sorted if 2 <= d <= 5]

    for quality_type in quality_types:
        if quality_placed >= 1 or session_count <= 0:  # Limit to 1 quality session for now
            break

        if not midweek_days:
            continue

        # Find a midweek day that respects constraints
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
                target_duration_seconds=int((template.duration_range_minutes[0] + template.duration_range_minutes[1]) / 2 * 60),
                intensity=template.intensity,
                hr_zone_primary=template.hr_zone_primary,
                blocks=template.blocks,
            )
            sessions.append(session)
            quality_placed += 1
            session_count -= 1
            midweek_days.remove(best_day)

    # Step 3: Fill remaining days with EF/REC
    used_days = {s.day_of_week for s in sessions}
    remaining_days = [d for d in available_days_sorted if d not in used_days]

    for day in remaining_days:
        if session_count <= 0:
            break

        # Choose EF or REC based on recovery needs
        session_type = SessionType.EF if quality_placed > 0 else SessionType.REC
        if session_type not in phase_types:
            session_type = SessionType.EF if SessionType.EF in phase_types else SessionType.REC

        if session_type in phase_types:
            template = get_session_template(session_type, experience, phase)
            session = SessionSpec(
                day_of_week=day,
                session_type=session_type,
                title=template.title,
                description=template.description,
                sport_type=template.sport_type,
                target_duration_seconds=int((template.duration_range_minutes[0] + template.duration_range_minutes[1]) / 2 * 60),
                intensity=template.intensity,
                hr_zone_primary=template.hr_zone_primary,
                blocks=template.blocks,
            )
            sessions.append(session)
            session_count -= 1

    # Step 4: Add RMU on non-running day if available and phase allows
    if SessionType.RMU in phase_types and not is_recovery_week:
        non_running_days = [d for d in range(1, 8) if d not in {s.day_of_week for s in sessions}]
        # Exclude days adjacent to hard sessions
        valid_rmu_days = [d for d in non_running_days if not _is_adjacent_to_hard(d, sessions)]

        if valid_rmu_days:
            template = get_session_template(SessionType.RMU, experience, phase)
            rmu_session = SessionSpec(
                day_of_week=valid_rmu_days[0],
                session_type=SessionType.RMU,
                title=template.title,
                description=template.description,
                sport_type=template.sport_type,
                target_duration_seconds=int((template.duration_range_minutes[0] + template.duration_range_minutes[1]) / 2 * 60),
                intensity=template.intensity,
                hr_zone_primary=template.hr_zone_primary,
                blocks=template.blocks,
            )
            sessions.append(rmu_session)

    # Sort by day of week
    sessions.sort(key=lambda s: s.day_of_week)

    return sessions


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
) -> SessionSpec:
    """Create a long run session from calculate_long_run output.

    Args:
        day: Day of week (1-7).
        experience: Athlete experience level.
        phase: Training phase.
        long_run_spec: Dict with target_km, target_duration_seconds, progression_note.

    Returns:
        SessionSpec for the long run.
    """
    template = get_session_template(SessionType.SL, experience, phase)

    return SessionSpec(
        day_of_week=day,
        session_type=SessionType.SL,
        title=template.title,
        description=template.description + f" ({long_run_spec.get('progression_note', '')})",
        sport_type=template.sport_type,
        target_duration_seconds=long_run_spec.get("target_duration_seconds", 0),
        target_distance_meters=long_run_spec.get("target_km", 0) * 1000,
        intensity=template.intensity,
        hr_zone_primary=template.hr_zone_primary,
        blocks=template.blocks,
    )


def _can_place_hard_session(day: int, existing_sessions: list[SessionSpec]) -> bool:
    """Check if a hard session can be placed on a given day.

    Constraint: No 2 consecutive hard days (need >= 1 easy day between Z3+ sessions).
    48+ hours between Z4-Z5 sessions.

    Args:
        day: Day of week (1-7).
        existing_sessions: List of already-placed sessions.

    Returns:
        True if a hard session can be placed on this day.
    """
    hard_zones = [3, 4, 5]

    # Check adjacent days
    adjacent_days = [day - 1, day + 1]
    for session in existing_sessions:
        if session.day_of_week in adjacent_days:
            if session.hr_zone_primary and session.hr_zone_primary in hard_zones:
                return False

    return True


def _is_adjacent_to_hard(day: int, existing_sessions: list[SessionSpec]) -> bool:
    """Check if a day is adjacent to a hard session.

    Used to avoid placing RMU next to hard runs.

    Args:
        day: Day of week (1-7).
        existing_sessions: List of already-placed sessions.

    Returns:
        True if the day is adjacent to a Z3+ session.
    """
    hard_zones = [3, 4, 5]
    adjacent_days = [day - 1, day + 1]

    for session in existing_sessions:
        if session.day_of_week in adjacent_days:
            if session.hr_zone_primary and session.hr_zone_primary in hard_zones:
                return True

    return False
