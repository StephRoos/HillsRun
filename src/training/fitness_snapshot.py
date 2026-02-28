"""Aggregate Garmin data from asyncpg into a UserFitnessData model."""

from typing import Optional

from .models import UserFitnessData


async def build_fitness_snapshot(pool, user_id: int) -> UserFitnessData:
    """Aggregate Garmin data from DB into a fitness snapshot.

    Queries multiple tables to build a comprehensive view of the athlete's
    current fitness level, used by the plan generator to calibrate training loads.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        UserFitnessData with available metrics filled in.
    """
    vo2_max = await _get_vo2_max(pool, user_id)
    resting_hr = await _get_avg_resting_hr(pool, user_id)
    weight_kg = await _get_recent_weight(pool, user_id)
    activity_metrics = await _get_activity_metrics(pool, user_id)
    training_readiness = await _get_training_readiness(pool, user_id)
    vma_kmh = await _get_vma(pool, user_id)
    avg_sleep_score = await _get_avg_sleep_score(pool, user_id)
    avg_hrv = await _get_avg_hrv(pool, user_id)

    return UserFitnessData(
        vo2_max=vo2_max,
        resting_hr=resting_hr,
        weight_kg=weight_kg,
        vma_kmh=vma_kmh,
        weekly_volume_km=activity_metrics.get("weekly_volume_km"),
        weekly_elevation_m=activity_metrics.get("weekly_elevation_m"),
        recent_long_run_km=activity_metrics.get("recent_long_run_km"),
        recent_long_run_duration_s=activity_metrics.get("recent_long_run_duration_s"),
        avg_training_readiness=training_readiness.get("avg_score"),
        chronic_load=training_readiness.get("chronic_load"),
        acute_load=training_readiness.get("acute_load"),
        avg_sleep_score=avg_sleep_score,
        avg_hrv=avg_hrv,
    )


async def _get_vo2_max(pool, user_id: int) -> Optional[float]:
    """Get latest VO2 max from fitness_metrics (last 7 days).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        VO2 max value or None.
    """
    query = """
        SELECT COALESCE(vo2_max_running, vo2_max) as vo2_max
        FROM fitness_metrics
        WHERE user_id = $1 AND calendar_date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY calendar_date DESC
        LIMIT 1
    """
    row = await pool.fetchrow(query, user_id)
    return row["vo2_max"] if row else None


async def _get_avg_resting_hr(pool, user_id: int) -> Optional[int]:
    """Get average resting heart rate (last 7 days).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        Average resting HR or None.
    """
    query = """
        SELECT AVG(resting_heart_rate)::INTEGER as avg_rhr
        FROM daily_summary
        WHERE user_id = $1
            AND calendar_date >= CURRENT_DATE - INTERVAL '7 days'
            AND resting_heart_rate IS NOT NULL
    """
    row = await pool.fetchrow(query, user_id)
    return row["avg_rhr"] if row and row["avg_rhr"] else None


async def _get_recent_weight(pool, user_id: int) -> Optional[float]:
    """Get most recent weight from body_composition (last 30 days).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        Weight in kg or None.
    """
    query = """
        SELECT weight_kg
        FROM body_composition
        WHERE user_id = $1 AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
        ORDER BY timestamp DESC
        LIMIT 1
    """
    row = await pool.fetchrow(query, user_id)
    return row["weight_kg"] if row else None


async def _get_activity_metrics(pool, user_id: int) -> dict:
    """Get running activity metrics from last 6 weeks.

    Calculates weekly volume, elevation, and longest run stats.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        Dictionary with weekly_volume_km, weekly_elevation_m,
        recent_long_run_km, and recent_long_run_duration_s.
    """
    query = """
        SELECT
            SUM(distance_meters) / 1000.0 / GREATEST(1, COUNT(DISTINCT DATE_TRUNC('week', start_timestamp))) as weekly_km,
            SUM(elevation_gain_meters)::INTEGER / GREATEST(1, COUNT(DISTINCT DATE_TRUNC('week', start_timestamp))) as weekly_elevation,
            MAX(distance_meters) / 1000.0 as max_distance_km,
            MAX(duration_seconds)::INTEGER as max_duration_s
        FROM activities
        WHERE user_id = $1
            AND start_timestamp >= CURRENT_DATE - INTERVAL '42 days'
            AND sport_type ILIKE '%running%'
    """
    row = await pool.fetchrow(query, user_id)
    if not row:
        return {}

    return {
        "weekly_volume_km": row["weekly_km"],
        "weekly_elevation_m": row["weekly_elevation"],
        "recent_long_run_km": row["max_distance_km"],
        "recent_long_run_duration_s": row["max_duration_s"],
    }


async def _get_training_readiness(pool, user_id: int) -> dict:
    """Get training readiness metrics (last 7 days).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        Dictionary with avg_score, chronic_load, and acute_load.
    """
    query = """
        SELECT
            AVG(score)::FLOAT as avg_score,
            AVG(chronic_load)::FLOAT as chronic_load,
            AVG(acute_load)::FLOAT as acute_load
        FROM training_readiness
        WHERE user_id = $1
            AND calendar_date >= CURRENT_DATE - INTERVAL '7 days'
    """
    row = await pool.fetchrow(query, user_id)
    if not row:
        return {}

    return {
        "avg_score": row["avg_score"],
        "chronic_load": row["chronic_load"],
        "acute_load": row["acute_load"],
    }


async def _get_vma(pool, user_id: int) -> Optional[float]:
    """Get VMA (Vitesse Maximale Aérobie) from garmin_user.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        VMA in km/h or None.
    """
    query = """
        SELECT manual_vma as vma
        FROM garmin_user
        WHERE user_id = $1
    """
    row = await pool.fetchrow(query, user_id)
    return row["vma"] if row else None


async def _get_avg_sleep_score(pool, user_id: int) -> Optional[float]:
    """Get average sleep score (last 7 days).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        Average sleep score or None.
    """
    query = """
        SELECT AVG(sleep_score)::FLOAT as avg_score
        FROM sleep_data
        WHERE user_id = $1
            AND calendar_date >= CURRENT_DATE - INTERVAL '7 days'
            AND sleep_score IS NOT NULL
    """
    row = await pool.fetchrow(query, user_id)
    return row["avg_score"] if row and row["avg_score"] else None


async def _get_avg_hrv(pool, user_id: int) -> Optional[float]:
    """Get average weekly HRV (last 7 days).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        Average weekly HRV or None.
    """
    query = """
        SELECT AVG(weekly_avg)::FLOAT as avg_hrv
        FROM hrv_data
        WHERE user_id = $1
            AND calendar_date >= CURRENT_DATE - INTERVAL '7 days'
            AND weekly_avg IS NOT NULL
    """
    row = await pool.fetchrow(query, user_id)
    return row["avg_hrv"] if row and row["avg_hrv"] else None
