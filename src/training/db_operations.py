"""Database operations for training plan tables."""

import json
import logging
from datetime import date
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================
# Athlete Profile Operations
# ============================================


async def get_athlete_profile(pool, user_id: int) -> Optional[dict[str, Any]]:
    """Fetch athlete profile for a user.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        Profile dict or None if not found.
    """
    row = await pool.fetchrow(
        "SELECT * FROM athlete_profiles WHERE user_id = $1", user_id
    )
    return dict(row) if row else None


async def upsert_athlete_profile(
    pool, user_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    """Create or update athlete profile.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        data: Profile fields.

    Returns:
        Created/updated profile dict.
    """
    # Build upsert query with only provided fields
    allowed = {
        "birth_date",
        "gender",
        "height_cm",
        "experience_level",
        "available_days_per_week",
        "available_slots",
        "injury_history",
        "has_hill_access",
        "has_gym_access",
        "fc_max",
        "fc_repos",
        "fthr",
        "day_preferences",
    }
    fields = {k: v for k, v in data.items() if k in allowed}

    # Serialize JSONB fields
    if "available_slots" in fields and isinstance(fields["available_slots"], dict):
        fields["available_slots"] = json.dumps(fields["available_slots"])
    if "day_preferences" in fields and isinstance(fields["day_preferences"], dict):
        fields["day_preferences"] = json.dumps(fields["day_preferences"])

    columns = ["user_id"] + list(fields.keys())
    values = [user_id] + list(fields.values())
    placeholders = [f"${i}" for i in range(1, len(values) + 1)]

    # Build ON CONFLICT SET clause
    update_parts = [f"{col} = EXCLUDED.{col}" for col in fields.keys()]
    update_clause = (
        ", ".join(update_parts) if update_parts else "user_id = EXCLUDED.user_id"
    )

    query = f"""
        INSERT INTO athlete_profiles ({", ".join(columns)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT (user_id) DO UPDATE SET {update_clause}
        RETURNING *
    """
    row = await pool.fetchrow(query, *values)
    return dict(row)


# ============================================
# Race Target Operations
# ============================================


async def create_race_target(
    pool, user_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    """Create a new race target.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        data: Race target fields.

    Returns:
        Created race target dict.
    """
    query = """
        INSERT INTO race_targets (
            user_id, race_name, race_date, distance_km,
            elevation_gain_m, elevation_loss_m, altitude_min_m, altitude_max_m,
            technical_percent, cutoff_hours, itra_points, objective, elevation_profile
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING *
    """
    row = await pool.fetchrow(
        query,
        user_id,
        data["race_name"],
        data["race_date"],
        data["distance_km"],
        data.get("elevation_gain_m", 0),
        data.get("elevation_loss_m", 0),
        data.get("altitude_min_m", 0),
        data.get("altitude_max_m", 0),
        data.get("technical_percent", 0),
        data.get("cutoff_hours"),
        data.get("itra_points"),
        data.get("objective", "finish"),
        json.dumps(data["elevation_profile"])
        if data.get("elevation_profile")
        else None,
    )
    return dict(row)


async def get_race_target(pool, race_id: int, user_id: int) -> Optional[dict[str, Any]]:
    """Fetch a race target by ID with ownership check.

    Args:
        pool: asyncpg connection pool.
        race_id: Race target ID.
        user_id: Garmin user ID.

    Returns:
        Race target dict or None if not found.
    """
    row = await pool.fetchrow(
        "SELECT * FROM race_targets WHERE id = $1 AND user_id = $2",
        race_id,
        user_id,
    )
    return dict(row) if row else None


async def list_race_targets(pool, user_id: int) -> list[dict[str, Any]]:
    """List all race targets for a user, ordered by race_date.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        List of race target dicts.
    """
    rows = await pool.fetch(
        "SELECT * FROM race_targets WHERE user_id = $1 ORDER BY race_date ASC",
        user_id,
    )
    return [dict(r) for r in rows]


async def delete_race_target(pool, race_id: int, user_id: int) -> bool:
    """Delete a race target.

    Args:
        pool: asyncpg connection pool.
        race_id: Race target ID.
        user_id: Garmin user ID.

    Returns:
        True if deleted, False otherwise.
    """
    result = await pool.execute(
        "DELETE FROM race_targets WHERE id = $1 AND user_id = $2",
        race_id,
        user_id,
    )
    return result == "DELETE 1"


# ============================================
# Training Plan Operations
# ============================================


async def create_training_plan(
    pool, user_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    """Create a new training plan (master entity).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        data: Training plan fields.

    Returns:
        Created training plan dict.
    """
    query = """
        INSERT INTO training_plans (
            user_id, race_target_id, name, status, start_date, end_date,
            total_weeks, experience_level, generation_params, created_by_user_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
    """
    row = await pool.fetchrow(
        query,
        user_id,
        data["race_target_id"],
        data["name"],
        data.get("status", "draft"),
        data["start_date"],
        data["end_date"],
        data["total_weeks"],
        data["experience_level"],
        json.dumps(data["generation_params"])
        if data.get("generation_params")
        else None,
        data.get("created_by_user_id"),
    )
    return dict(row)


async def get_training_plan(
    pool, plan_id: int, user_id: int
) -> Optional[dict[str, Any]]:
    """Fetch a training plan with ownership check.

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.
        user_id: Garmin user ID.

    Returns:
        Training plan dict or None if not found.
    """
    row = await pool.fetchrow(
        "SELECT * FROM training_plans WHERE id = $1 AND user_id = $2",
        plan_id,
        user_id,
    )
    return dict(row) if row else None


async def list_training_plans(
    pool, user_id: int, limit: int = 50, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    """List training plans for a user with pagination.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        limit: Maximum number of results.
        offset: Number of results to skip.

    Returns:
        Tuple of (list of training plan dicts, total count).
    """
    total = await pool.fetchval(
        "SELECT COUNT(*) FROM training_plans WHERE user_id = $1", user_id
    )
    rows = await pool.fetch(
        "SELECT * FROM training_plans WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        user_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows], total


async def update_training_plan_status(
    pool, plan_id: int, user_id: int, status: str
) -> Optional[dict[str, Any]]:
    """Update training plan status (draft/active/completed/cancelled).

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.
        user_id: Garmin user ID.
        status: New status value.

    Returns:
        Updated training plan dict or None if not found.
    """
    row = await pool.fetchrow(
        "UPDATE training_plans SET status = $1 WHERE id = $2 AND user_id = $3 RETURNING *",
        status,
        plan_id,
        user_id,
    )
    return dict(row) if row else None


async def delete_training_plan(pool, plan_id: int, user_id: int) -> bool:
    """Delete a training plan (cascades to weeks, sessions, and planned workouts).

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.
        user_id: Garmin user ID.

    Returns:
        True if deleted, False otherwise.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Delete associated planned workouts from calendar first
            await conn.execute(
                "DELETE FROM planned_workouts WHERE plan_id = $1 AND user_id = $2",
                plan_id,
                user_id,
            )
            result = await conn.execute(
                "DELETE FROM training_plans WHERE id = $1 AND user_id = $2",
                plan_id,
                user_id,
            )
            return result == "DELETE 1"


# ============================================
# Plan Week Operations
# ============================================


async def create_plan_week(pool, plan_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Create a training plan week.

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.
        data: Training plan week fields.

    Returns:
        Created training plan week dict.
    """
    query = """
        INSERT INTO training_plan_weeks (
            plan_id, week_number, phase, is_recovery_week,
            target_tss, target_volume_km, target_elevation_m, target_sessions, notes
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
    """
    row = await pool.fetchrow(
        query,
        plan_id,
        data["week_number"],
        data["phase"],
        data.get("is_recovery_week", False),
        data.get("target_tss"),
        data.get("target_volume_km"),
        data.get("target_elevation_m"),
        data.get("target_sessions"),
        data.get("notes"),
    )
    return dict(row)


async def get_plan_weeks(pool, plan_id: int) -> list[dict[str, Any]]:
    """Fetch all weeks for a plan, ordered by week_number.

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.

    Returns:
        List of training plan week dicts.
    """
    rows = await pool.fetch(
        "SELECT * FROM training_plan_weeks WHERE plan_id = $1 ORDER BY week_number ASC",
        plan_id,
    )
    return [dict(r) for r in rows]


async def get_plan_week_by_number(
    pool, plan_id: int, week_number: int
) -> Optional[dict[str, Any]]:
    """Fetch a specific week by plan and week number.

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.
        week_number: Week number within the plan.

    Returns:
        Training plan week dict or None if not found.
    """
    row = await pool.fetchrow(
        "SELECT * FROM training_plan_weeks WHERE plan_id = $1 AND week_number = $2",
        plan_id,
        week_number,
    )
    return dict(row) if row else None


# ============================================
# Plan Session Operations
# ============================================


async def create_plan_session(pool, data: dict[str, Any]) -> dict[str, Any]:
    """Create a training plan session.

    Args:
        pool: asyncpg connection pool.
        data: Training plan session fields.

    Returns:
        Created training plan session dict.
    """
    query = """
        INSERT INTO training_plan_sessions (
            plan_id, week_id, planned_workout_id, day_of_week,
            session_type, title, description, sport_type,
            target_duration_seconds, target_distance_meters, target_elevation_gain_m,
            target_tss, hr_zone_primary, intensity, blocks, sort_order
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        RETURNING *
    """
    blocks = data.get("blocks")
    if blocks and not isinstance(blocks, str):
        blocks = json.dumps(
            [b.model_dump() if hasattr(b, "model_dump") else b for b in blocks]
        )

    row = await pool.fetchrow(
        query,
        data["plan_id"],
        data["week_id"],
        data.get("planned_workout_id"),
        data["day_of_week"],
        data["session_type"],
        data["title"],
        data.get("description"),
        data.get("sport_type", "trail_running"),
        data.get("target_duration_seconds"),
        data.get("target_distance_meters"),
        data.get("target_elevation_gain_m"),
        data.get("target_tss"),
        data.get("hr_zone_primary"),
        data.get("intensity", "moderate"),
        blocks,
        data.get("sort_order", 0),
    )
    return dict(row)


async def get_plan_sessions_for_week(pool, week_id: int) -> list[dict[str, Any]]:
    """Fetch all sessions for a plan week, ordered by day and sort_order.

    Args:
        pool: asyncpg connection pool.
        week_id: Training plan week ID.

    Returns:
        List of training plan session dicts.
    """
    rows = await pool.fetch(
        "SELECT * FROM training_plan_sessions WHERE week_id = $1 ORDER BY day_of_week ASC, sort_order ASC",
        week_id,
    )
    return [dict(r) for r in rows]


async def get_plan_sessions(pool, plan_id: int) -> list[dict[str, Any]]:
    """Fetch all sessions for a plan, ordered by week and day.

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.

    Returns:
        List of training plan session dicts.
    """
    rows = await pool.fetch(
        """SELECT s.* FROM training_plan_sessions s
           JOIN training_plan_weeks w ON s.week_id = w.id
           WHERE s.plan_id = $1
           ORDER BY w.week_number ASC, s.day_of_week ASC, s.sort_order ASC""",
        plan_id,
    )
    return [dict(r) for r in rows]


# ============================================
# Planned Workout Creation (links sessions to calendar)
# ============================================


async def create_planned_workout_for_session(
    pool, user_id: int, plan_id: int, session_data: dict[str, Any], workout_date: date
) -> dict[str, Any]:
    """Create a planned_workouts entry linked to a training plan session.

    Extends the existing planned_workouts table with plan-specific columns.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        plan_id: Training plan ID.
        session_data: Training plan session data.
        workout_date: Planned workout date.

    Returns:
        Created planned workout dict.
    """
    blocks = session_data.get("blocks")
    if blocks and not isinstance(blocks, str):
        blocks = json.dumps(
            [b.model_dump() if hasattr(b, "model_dump") else b for b in blocks]
        )

    query = """
        INSERT INTO planned_workouts (
            user_id, planned_date, sport_type, title, description,
            planned_duration_seconds, planned_distance_meters, intensity,
            plan_id, session_type, hr_zone_primary, target_elevation_gain_m, blocks
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING *
    """
    row = await pool.fetchrow(
        query,
        user_id,
        workout_date,
        session_data.get("sport_type", "trail_running"),
        session_data["title"],
        session_data.get("description"),
        session_data.get("target_duration_seconds"),
        session_data.get("target_distance_meters"),
        session_data.get("intensity", "moderate"),
        plan_id,
        session_data.get("session_type"),
        session_data.get("hr_zone_primary"),
        session_data.get("target_elevation_gain_m"),
        blocks,
    )
    return dict(row)
