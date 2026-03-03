"""Training plan generator — orchestrates all engine modules."""

import json
import logging
from datetime import date, timedelta
from typing import Any, Optional

from .models import (
    DayPreferences,
    ExperienceLevel,
    GeneratePlanRequest,
    RaceObjective,
)
from . import db_operations as db_ops
from .fitness_snapshot import build_fitness_snapshot
from .hr_zones import calculate_hr_zones
from .load_calculator import calculate_session_tss, validate_weekly_progression
from .long_run import calculate_long_run
from .periodization import build_periodization
from .race_classifier import classify_race
from .week_builder import build_week

logger = logging.getLogger(__name__)


async def generate_plan(
    pool,
    user_id: int,
    request: GeneratePlanRequest,
    coach_id: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a complete training plan.

    Orchestration workflow:
    1. Build fitness snapshot from Garmin data
    2. Load athlete profile
    3. Load race target
    4. Classify race
    5. Calculate HR zones
    6. Build periodization
    7. For each week: build sessions, calculate long run, validate load
    8. Save all to DB in a transaction
    9. Return plan ID and summary

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        request: Plan generation request with race_target_id etc.
        coach_id: Optional Better-Auth coach ID.

    Returns:
        Dict with plan_id and summary info.

    Raises:
        ValueError: If profile or race target not found.
    """
    # Step 1: Build fitness snapshot
    fitness = await build_fitness_snapshot(pool, user_id)
    logger.info(
        f"Fitness snapshot for user {user_id}: VO2max={fitness.vo2_max}, "
        f"weekly_km={fitness.weekly_volume_km}"
    )

    # Step 2: Load athlete profile
    profile = await db_ops.get_athlete_profile(pool, user_id)
    if not profile:
        raise ValueError("Athlete profile not found. Please create a profile first.")

    experience = ExperienceLevel(profile.get("experience_level", "intermediate"))

    # Step 3: Load race target
    race = await db_ops.get_race_target(pool, request.race_target_id, user_id)
    if not race:
        raise ValueError("Race target not found.")

    # Step 4: Classify race
    race_flags = classify_race(
        distance_km=float(race["distance_km"]),
        elevation_gain_m=race.get("elevation_gain_m", 0) or 0,
        technical_percent=race.get("technical_percent", 0) or 0,
        altitude_max_m=race.get("altitude_max_m", 0) or 0,
    )

    # Step 5: Calculate HR zones
    fc_max = profile.get("fc_max") or fitness.max_hr
    fc_repos = profile.get("fc_repos") or fitness.resting_hr

    # Determine age from birth_date if needed for HR estimation
    age = None
    if profile.get("birth_date"):
        today = date.today()
        bd = profile["birth_date"]
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    hr_zones = None
    if fc_max or age:
        hr_zones = calculate_hr_zones(fc_max=fc_max, fc_repos=fc_repos, age=age)

    # Extract race objective
    objective_str = race.get("objective", "finish")
    objective = RaceObjective(objective_str) if objective_str else RaceObjective.finish

    # Step 6: Determine plan duration and dates
    race_date = race["race_date"]
    if request.total_weeks:
        total_weeks = request.total_weeks
    else:
        # Auto-calculate: weeks from start_date (or today) to race_date
        start = request.start_date or date.today()
        total_weeks = max(6, (race_date - start).days // 7)
        total_weeks = min(total_weeks, 30)

    start_date = request.start_date or (race_date - timedelta(weeks=total_weeks))
    end_date = race_date

    # Step 7: Build periodization
    weeks = build_periodization(total_weeks, experience, race_flags.category)

    # Step 8: Determine plan name
    plan_name = request.plan_name or f"Plan {race['race_name']} - {total_weeks} weeks"

    # Step 9: Resolve available days and day preferences before saving
    available_days = _resolve_available_days(profile)
    day_prefs = _resolve_day_preferences(profile, request.day_preferences)

    # Step 10: Save plan and weeks/sessions in a transaction
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Create master plan
            plan_row = await conn.fetchrow(
                """INSERT INTO training_plans (
                    user_id, race_target_id, name, status, start_date, end_date,
                    total_weeks, experience_level, generation_params, created_by_user_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING *""",
                user_id,
                request.race_target_id,
                plan_name,
                "draft",
                start_date,
                end_date,
                total_weeks,
                experience.value,
                json.dumps({
                    "race_flags": race_flags.model_dump(),
                    "fitness_snapshot": fitness.model_dump(),
                    "experience": experience.value,
                    "objective": objective.value,
                    "hr_zones": [z.model_dump() for z in hr_zones] if hr_zones else None,
                    "day_preferences": day_prefs.model_dump() if day_prefs else None,
                }),
                coach_id,
            )
            plan_id = plan_row["id"]

            current_long_run_km = fitness.recent_long_run_km or 0
            previous_week_tss = 0.0
            race_distance_km = float(race["distance_km"])

            for week_spec in weeks:
                # Calculate long run for this week
                long_run_spec = calculate_long_run(
                    week_number=week_spec.week_number,
                    total_weeks=total_weeks,
                    phase=week_spec.phase,
                    is_recovery_week=week_spec.is_recovery_week,
                    experience=experience,
                    race_distance_km=race_distance_km,
                    current_long_run_km=current_long_run_km,
                )

                # Build week sessions (preferences are best-effort, constraints win)
                sessions = build_week(
                    available_days=available_days,
                    phase=week_spec.phase,
                    experience=experience,
                    is_recovery_week=week_spec.is_recovery_week,
                    week_number=week_spec.week_number,
                    long_run_spec=long_run_spec,
                    race_flags=race_flags,
                    objective=objective,
                    day_preferences=day_prefs,
                )

                # Inject personalized HR zones into sessions
                if hr_zones:
                    for s in sessions:
                        if s.hr_zone_primary:
                            zone = next((z for z in hr_zones if z.zone == s.hr_zone_primary), None)
                            if zone:
                                for block in s.blocks:
                                    if block.hr_zone == s.hr_zone_primary:
                                        block.description += f" ({zone.hr_min}-{zone.hr_max} bpm)"

                # Calculate total TSS for validation
                week_tss = sum(
                    calculate_session_tss(
                        s.session_type,
                        s.target_duration_seconds or 0,
                        s.target_elevation_gain_m or 0,
                    )
                    for s in sessions
                )

                # Validate progression (skip first week)
                if previous_week_tss > 0 and not week_spec.is_recovery_week:
                    is_valid, max_tss = validate_weekly_progression(week_tss, previous_week_tss)
                    if not is_valid:
                        # Scale down sessions proportionally
                        scale = max_tss / week_tss if week_tss > 0 else 1.0
                        for s in sessions:
                            if s.target_duration_seconds:
                                s.target_duration_seconds = int(s.target_duration_seconds * scale)
                        week_tss = max_tss

                if not week_spec.is_recovery_week:
                    previous_week_tss = week_tss

                # Create week in DB
                week_row = await conn.fetchrow(
                    """INSERT INTO training_plan_weeks (
                        plan_id, week_number, phase, is_recovery_week,
                        target_tss, target_volume_km, target_sessions, notes
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
                    plan_id,
                    week_spec.week_number,
                    week_spec.phase.value,
                    week_spec.is_recovery_week,
                    round(week_tss, 1),
                    long_run_spec["target_km"],
                    len(sessions),
                    long_run_spec.get("progression_note", ""),
                )
                week_id = week_row["id"]

                # Calculate the actual date for each session
                week_start = start_date + timedelta(weeks=week_spec.week_number - 1)
                # week_start is Monday of that week

                for idx, session in enumerate(sessions):
                    # Calculate workout date (week_start is Monday = day 1)
                    workout_date = week_start + timedelta(days=session.day_of_week - 1)

                    blocks_json = None
                    if session.blocks:
                        blocks_json = json.dumps([b.model_dump() for b in session.blocks])

                    session_tss = calculate_session_tss(
                        session.session_type,
                        session.target_duration_seconds or 0,
                        session.target_elevation_gain_m or 0,
                    )

                    # Create planned_workout entry (for calendar)
                    pw_row = await conn.fetchrow(
                        """INSERT INTO planned_workouts (
                            user_id, planned_date, sport_type, title, description,
                            planned_duration_seconds, planned_distance_meters, intensity,
                            plan_id, session_type, hr_zone_primary, target_elevation_gain_m, blocks
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        RETURNING id""",
                        user_id,
                        workout_date,
                        session.sport_type,
                        session.title,
                        session.description,
                        session.target_duration_seconds,
                        session.target_distance_meters,
                        session.intensity.value if hasattr(session.intensity, 'value') else str(session.intensity),
                        plan_id,
                        session.session_type.value if hasattr(session.session_type, 'value') else str(session.session_type),
                        session.hr_zone_primary,
                        session.target_elevation_gain_m,
                        blocks_json,
                    )
                    planned_workout_id = pw_row["id"]

                    # Create plan session entry
                    await conn.fetchrow(
                        """INSERT INTO training_plan_sessions (
                            plan_id, week_id, planned_workout_id, day_of_week,
                            session_type, title, description, sport_type,
                            target_duration_seconds, target_distance_meters,
                            target_elevation_gain_m, target_tss, hr_zone_primary,
                            intensity, blocks, sort_order
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                        RETURNING id""",
                        plan_id,
                        week_id,
                        planned_workout_id,
                        session.day_of_week,
                        session.session_type.value if hasattr(session.session_type, 'value') else str(session.session_type),
                        session.title,
                        session.description,
                        session.sport_type,
                        session.target_duration_seconds,
                        session.target_distance_meters,
                        session.target_elevation_gain_m,
                        round(session_tss, 1),
                        session.hr_zone_primary,
                        session.intensity.value if hasattr(session.intensity, 'value') else str(session.intensity),
                        blocks_json,
                        idx,
                    )

    logger.info(
        f"Generated plan {plan_id} for user {user_id}: {total_weeks} weeks, "
        f"{race_flags.category.value}"
    )

    return {
        "plan_id": plan_id,
        "name": plan_name,
        "total_weeks": total_weeks,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "race_category": race_flags.category.value,
        "experience_level": experience.value,
        "status": "draft",
    }


def _resolve_day_preferences(
    profile: dict,
    request_override: Optional[DayPreferences] = None,
) -> Optional[DayPreferences]:
    """Resolve day preferences: request override > profile > None.

    Args:
        profile: Athlete profile dict from DB.
        request_override: Optional override from the generation request.

    Returns:
        DayPreferences if any source provides them, else None.
    """
    # Request-level override takes full priority
    if request_override:
        return request_override

    # Fall back to profile-stored preferences
    prefs = profile.get("day_preferences")
    if prefs and isinstance(prefs, dict):
        return DayPreferences(**prefs)

    return None


# Day name → ISO day number (1=Monday, 7=Sunday)
_DAY_NAME_MAP = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "lundi": 1, "mardi": 2, "mercredi": 3, "jeudi": 4,
    "vendredi": 5, "samedi": 6, "dimanche": 7,
}


def _resolve_available_days(profile: dict) -> list[int]:
    """Resolve available training days from athlete profile.

    Uses available_slots JSONB if present (keys are day names, values are
    time slot arrays). Falls back to available_days_per_week integer with
    a heuristic spread.

    Args:
        profile: Athlete profile dict from DB.

    Returns:
        Sorted list of day numbers (1=Monday, 7=Sunday).
    """
    # Prefer available_slots JSONB when present
    slots = profile.get("available_slots")
    if slots and isinstance(slots, dict):
        days = []
        for day_name in slots:
            day_num = _DAY_NAME_MAP.get(day_name.lower())
            if day_num and slots[day_name]:  # Only include if slot list is non-empty
                days.append(day_num)
        if days:
            return sorted(set(days))

    # Fallback to integer heuristic
    days_per_week = profile.get("available_days_per_week", 4) or 4
    if days_per_week >= 7:
        return list(range(1, 8))
    if days_per_week >= 5:
        return [1, 2, 3, 4, 5, 6, 7][:days_per_week]
    if days_per_week == 4:
        return [2, 4, 6, 7]  # Tue, Thu, Sat, Sun
    if days_per_week == 3:
        return [2, 5, 6]  # Tue, Fri, Sat
    return [4, 6]  # Thu, Sat
