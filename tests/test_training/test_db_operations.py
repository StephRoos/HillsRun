"""Tests for training plan database operations."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.training.db_operations import (
    create_plan_session,
    create_plan_week,
    create_planned_workout_for_session,
    create_race_target,
    create_training_plan,
    delete_race_target,
    delete_training_plan,
    get_athlete_profile,
    get_plan_sessions,
    get_plan_sessions_for_week,
    get_plan_week_by_number,
    get_plan_weeks,
    get_race_target,
    get_training_plan,
    list_race_targets,
    list_training_plans,
    update_training_plan_status,
    upsert_athlete_profile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pool(**kwargs):
    """Create a mock asyncpg pool with sensible defaults."""
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=kwargs.get("fetchrow", None))
    pool.fetch = AsyncMock(return_value=kwargs.get("fetch", []))
    pool.fetchval = AsyncMock(return_value=kwargs.get("fetchval", 0))
    pool.execute = AsyncMock(return_value=kwargs.get("execute", "DELETE 0"))
    return pool


def make_conn_pool(execute_result="DELETE 1"):
    """Create a mock pool with acquire() and transaction() context managers.

    Both pool.acquire() and conn.transaction() must be synchronous calls that
    return objects supporting the async context manager protocol (__aenter__
    / __aexit__). Using MagicMock (not AsyncMock) for these avoids the
    'coroutine object does not support async context manager' error.
    """
    from unittest.mock import MagicMock

    # conn.execute is called with await, so it must be an AsyncMock
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(return_value=execute_result)

    # conn.transaction() is called as `async with conn.transaction():`
    transaction_cm = MagicMock()
    transaction_cm.__aenter__ = AsyncMock(return_value=None)
    transaction_cm.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction.return_value = transaction_cm

    # pool.acquire() is called as `async with pool.acquire() as conn:`
    acquire_cm = MagicMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire.return_value = acquire_cm

    return pool, mock_conn


# ---------------------------------------------------------------------------
# Athlete Profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_athlete_profile_found():
    row = {"user_id": 1, "gender": "male", "height_cm": 175}
    pool = make_pool(fetchrow=row)
    result = await get_athlete_profile(pool, user_id=1)
    assert result == dict(row)
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_athlete_profile_not_found():
    pool = make_pool(fetchrow=None)
    result = await get_athlete_profile(pool, user_id=99)
    assert result is None


@pytest.mark.asyncio
async def test_upsert_athlete_profile_basic_fields():
    row = {"user_id": 1, "gender": "female", "height_cm": 165}
    pool = make_pool(fetchrow=row)
    data = {"gender": "female", "height_cm": 165}
    result = await upsert_athlete_profile(pool, user_id=1, data=data)
    assert result == dict(row)
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_athlete_profile_serializes_available_slots():
    row = {"user_id": 1, "available_slots": '{"monday": "morning"}'}
    pool = make_pool(fetchrow=row)
    data = {"available_slots": {"monday": "morning"}}
    await upsert_athlete_profile(pool, user_id=1, data=data)
    # The query call args should contain the JSON-serialized string, not the dict
    call_args = pool.fetchrow.call_args
    positional_args = call_args[0]
    assert any(isinstance(a, str) and "monday" in a for a in positional_args)


@pytest.mark.asyncio
async def test_upsert_athlete_profile_serializes_day_preferences():
    row = {"user_id": 1, "day_preferences": '{"long_run": 6}'}
    pool = make_pool(fetchrow=row)
    data = {"day_preferences": {"long_run": 6}}
    await upsert_athlete_profile(pool, user_id=1, data=data)
    call_args = pool.fetchrow.call_args
    positional_args = call_args[0]
    assert any(isinstance(a, str) and "long_run" in a for a in positional_args)


@pytest.mark.asyncio
async def test_get_athlete_profile_decodes_jsonb_string_to_dict():
    # asyncpg returns JSONB columns as raw strings (no codec on the pool);
    # the profile must come back with day_preferences parsed to a dict.
    row = {"user_id": 1, "day_preferences": '{"long_run": 6, "quality": [2]}'}
    pool = make_pool(fetchrow=row)
    result = await get_athlete_profile(pool, user_id=1)
    assert result["day_preferences"] == {"long_run": 6, "quality": [2]}


@pytest.mark.asyncio
async def test_upsert_athlete_profile_decodes_jsonb_on_return():
    # The RETURNING * row also carries JSONB as a string → decode before returning.
    row = {"user_id": 1, "day_preferences": '{"long_run": 6}'}
    pool = make_pool(fetchrow=row)
    data = {"day_preferences": {"long_run": 6}}
    result = await upsert_athlete_profile(pool, user_id=1, data=data)
    assert result["day_preferences"] == {"long_run": 6}


@pytest.mark.asyncio
async def test_upsert_athlete_profile_ignores_unknown_fields():
    row = {"user_id": 1, "height_cm": 180}
    pool = make_pool(fetchrow=row)
    data = {"height_cm": 180, "unknown_field": "ignored", "another_bad_field": 42}
    result = await upsert_athlete_profile(pool, user_id=1, data=data)
    assert result == dict(row)
    # Query should not reference unknown fields
    query = pool.fetchrow.call_args[0][0]
    assert "unknown_field" not in query
    assert "another_bad_field" not in query


@pytest.mark.asyncio
async def test_upsert_athlete_profile_no_fields_uses_fallback():
    row = {"user_id": 1}
    pool = make_pool(fetchrow=row)
    # No allowed fields provided — ON CONFLICT clause should use fallback
    data = {"not_a_real_field": "value"}
    await upsert_athlete_profile(pool, user_id=1, data=data)
    query = pool.fetchrow.call_args[0][0]
    assert "user_id = EXCLUDED.user_id" in query


# ---------------------------------------------------------------------------
# Race Targets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_race_target_minimal():
    row = {"id": 10, "user_id": 1, "race_name": "UTMB", "distance_km": 170.0}
    pool = make_pool(fetchrow=row)
    data = {
        "race_name": "UTMB",
        "race_date": date(2026, 8, 28),
        "distance_km": 170.0,
    }
    result = await create_race_target(pool, user_id=1, data=data)
    assert result == dict(row)
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_race_target_with_elevation_profile():
    row = {"id": 11, "user_id": 1, "race_name": "CCC"}
    pool = make_pool(fetchrow=row)
    data = {
        "race_name": "CCC",
        "race_date": date(2026, 8, 29),
        "distance_km": 100.0,
        "elevation_profile": {"km": [0, 50, 100], "alt": [800, 2500, 1200]},
    }
    await create_race_target(pool, user_id=1, data=data)
    # elevation_profile should be JSON-serialized when passed
    call_args = pool.fetchrow.call_args[0]
    assert any(isinstance(a, str) and "km" in a for a in call_args)


@pytest.mark.asyncio
async def test_get_race_target_found():
    row = {"id": 10, "user_id": 1, "race_name": "UTMB"}
    pool = make_pool(fetchrow=row)
    result = await get_race_target(pool, race_id=10, user_id=1)
    assert result == dict(row)


@pytest.mark.asyncio
async def test_get_race_target_not_found():
    pool = make_pool(fetchrow=None)
    result = await get_race_target(pool, race_id=99, user_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_list_race_targets_returns_list():
    rows = [
        {"id": 1, "race_name": "TDS"},
        {"id": 2, "race_name": "OCC"},
    ]
    pool = make_pool(fetch=rows)
    result = await list_race_targets(pool, user_id=1)
    assert len(result) == 2
    assert result[0] == dict(rows[0])
    assert result[1] == dict(rows[1])


@pytest.mark.asyncio
async def test_list_race_targets_empty():
    pool = make_pool(fetch=[])
    result = await list_race_targets(pool, user_id=1)
    assert result == []


@pytest.mark.asyncio
async def test_delete_race_target_success():
    pool = make_pool(execute="DELETE 1")
    result = await delete_race_target(pool, race_id=10, user_id=1)
    assert result is True


@pytest.mark.asyncio
async def test_delete_race_target_not_found():
    pool = make_pool(execute="DELETE 0")
    result = await delete_race_target(pool, race_id=99, user_id=1)
    assert result is False


# ---------------------------------------------------------------------------
# Training Plans
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_training_plan_basic():
    row = {"id": 5, "user_id": 1, "name": "Plan UTMB", "status": "draft"}
    pool = make_pool(fetchrow=row)
    data = {
        "race_target_id": 10,
        "name": "Plan UTMB",
        "start_date": date(2025, 12, 1),
        "end_date": date(2026, 8, 28),
        "total_weeks": 36,
        "experience_level": "intermediate",
    }
    result = await create_training_plan(pool, user_id=1, data=data)
    assert result == dict(row)
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_training_plan_serializes_generation_params():
    row = {"id": 5, "user_id": 1, "name": "Plan"}
    pool = make_pool(fetchrow=row)
    data = {
        "race_target_id": 10,
        "name": "Plan",
        "start_date": date(2025, 12, 1),
        "end_date": date(2026, 8, 28),
        "total_weeks": 36,
        "experience_level": "advanced",
        "generation_params": {"v": 1, "algo": "periodized"},
    }
    await create_training_plan(pool, user_id=1, data=data)
    call_args = pool.fetchrow.call_args[0]
    assert any(isinstance(a, str) and "algo" in a for a in call_args)


@pytest.mark.asyncio
async def test_get_training_plan_found():
    row = {"id": 5, "user_id": 1, "name": "Plan UTMB"}
    pool = make_pool(fetchrow=row)
    result = await get_training_plan(pool, plan_id=5, user_id=1)
    assert result == dict(row)


@pytest.mark.asyncio
async def test_get_training_plan_not_found():
    pool = make_pool(fetchrow=None)
    result = await get_training_plan(pool, plan_id=999, user_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_list_training_plans_returns_tuple():
    rows = [{"id": 1, "name": "Plan A"}, {"id": 2, "name": "Plan B"}]
    pool = make_pool(fetch=rows, fetchval=2)
    plans, total = await list_training_plans(pool, user_id=1)
    assert total == 2
    assert len(plans) == 2
    assert plans[0] == dict(rows[0])


@pytest.mark.asyncio
async def test_list_training_plans_pagination():
    pool = make_pool(fetch=[], fetchval=10)
    plans, total = await list_training_plans(pool, user_id=1, limit=5, offset=5)
    assert total == 10
    assert plans == []
    # Verify limit and offset were passed
    call_args = pool.fetch.call_args[0]
    assert 5 in call_args


@pytest.mark.asyncio
async def test_update_training_plan_status_found():
    row = {"id": 5, "status": "active"}
    pool = make_pool(fetchrow=row)
    result = await update_training_plan_status(pool, plan_id=5, user_id=1, status="active")
    assert result == dict(row)
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_update_training_plan_status_not_found():
    pool = make_pool(fetchrow=None)
    result = await update_training_plan_status(pool, plan_id=999, user_id=1, status="active")
    assert result is None


@pytest.mark.asyncio
async def test_delete_training_plan_success():
    pool, mock_conn = make_conn_pool(execute_result="DELETE 1")
    result = await delete_training_plan(pool, plan_id=5, user_id=1)
    assert result is True
    # Two execute calls: delete planned_workouts + delete training_plans
    assert mock_conn.execute.await_count == 2


@pytest.mark.asyncio
async def test_delete_training_plan_not_found():
    pool, mock_conn = make_conn_pool(execute_result="DELETE 0")
    result = await delete_training_plan(pool, plan_id=999, user_id=1)
    assert result is False


@pytest.mark.asyncio
async def test_delete_training_plan_deletes_planned_workouts_first():
    """Ensure planned_workouts are deleted before training_plans in transaction."""
    pool, mock_conn = make_conn_pool(execute_result="DELETE 1")
    await delete_training_plan(pool, plan_id=5, user_id=1)
    first_call_sql = mock_conn.execute.call_args_list[0][0][0]
    second_call_sql = mock_conn.execute.call_args_list[1][0][0]
    assert "planned_workouts" in first_call_sql
    assert "training_plans" in second_call_sql


# ---------------------------------------------------------------------------
# Plan Weeks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_plan_week_minimal():
    row = {"id": 20, "plan_id": 5, "week_number": 1, "phase": "base"}
    pool = make_pool(fetchrow=row)
    data = {"week_number": 1, "phase": "base"}
    result = await create_plan_week(pool, plan_id=5, data=data)
    assert result == dict(row)
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_plan_week_with_optional_fields():
    row = {"id": 21, "plan_id": 5, "week_number": 2, "phase": "development", "is_recovery_week": True}
    pool = make_pool(fetchrow=row)
    data = {
        "week_number": 2,
        "phase": "development",
        "is_recovery_week": True,
        "target_volume_km": 80.0,
        "target_sessions": 5,
    }
    result = await create_plan_week(pool, plan_id=5, data=data)
    assert result["is_recovery_week"] is True


@pytest.mark.asyncio
async def test_get_plan_weeks_returns_ordered_list():
    rows = [
        {"id": 1, "week_number": 1},
        {"id": 2, "week_number": 2},
    ]
    pool = make_pool(fetch=rows)
    result = await get_plan_weeks(pool, plan_id=5)
    assert len(result) == 2
    assert result[0]["week_number"] == 1


@pytest.mark.asyncio
async def test_get_plan_weeks_empty():
    pool = make_pool(fetch=[])
    result = await get_plan_weeks(pool, plan_id=5)
    assert result == []


@pytest.mark.asyncio
async def test_get_plan_week_by_number_found():
    row = {"id": 1, "plan_id": 5, "week_number": 3}
    pool = make_pool(fetchrow=row)
    result = await get_plan_week_by_number(pool, plan_id=5, week_number=3)
    assert result == dict(row)


@pytest.mark.asyncio
async def test_get_plan_week_by_number_not_found():
    pool = make_pool(fetchrow=None)
    result = await get_plan_week_by_number(pool, plan_id=5, week_number=99)
    assert result is None


# ---------------------------------------------------------------------------
# Plan Sessions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_plan_session_basic():
    row = {"id": 100, "plan_id": 5, "week_id": 20, "title": "EF 60min"}
    pool = make_pool(fetchrow=row)
    data = {
        "plan_id": 5,
        "week_id": 20,
        "day_of_week": 1,
        "session_type": "EF",
        "title": "EF 60min",
    }
    result = await create_plan_session(pool, data=data)
    assert result == dict(row)
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_plan_session_serializes_blocks_list():
    row = {"id": 101, "plan_id": 5, "week_id": 20, "title": "INT"}
    pool = make_pool(fetchrow=row)
    blocks = [{"name": "Warm-up", "duration_seconds": 600, "description": "easy"}]
    data = {
        "plan_id": 5,
        "week_id": 20,
        "day_of_week": 3,
        "session_type": "INT",
        "title": "INT",
        "blocks": blocks,
    }
    await create_plan_session(pool, data=data)
    call_args = pool.fetchrow.call_args[0]
    # blocks argument should be a JSON string
    assert any(isinstance(a, str) and "Warm-up" in a for a in call_args)


@pytest.mark.asyncio
async def test_create_plan_session_blocks_already_string():
    row = {"id": 102, "plan_id": 5, "week_id": 20, "title": "TMP"}
    pool = make_pool(fetchrow=row)
    blocks_str = '[{"name": "Tempo", "duration_seconds": 1800, "description": ""}]'
    data = {
        "plan_id": 5,
        "week_id": 20,
        "day_of_week": 2,
        "session_type": "TMP",
        "title": "TMP",
        "blocks": blocks_str,
    }
    await create_plan_session(pool, data=data)
    call_args = pool.fetchrow.call_args[0]
    # Pre-serialized string should be passed as-is
    assert blocks_str in call_args


@pytest.mark.asyncio
async def test_create_plan_session_blocks_with_model_dump():
    """Blocks that have model_dump() should be serialized correctly."""
    row = {"id": 103, "plan_id": 5, "week_id": 20, "title": "COT"}
    pool = make_pool(fetchrow=row)

    mock_block = MagicMock()
    mock_block.model_dump.return_value = {"name": "Cote", "duration_seconds": 300, "description": "uphill"}

    data = {
        "plan_id": 5,
        "week_id": 20,
        "day_of_week": 4,
        "session_type": "COT",
        "title": "COT",
        "blocks": [mock_block],
    }
    await create_plan_session(pool, data=data)
    call_args = pool.fetchrow.call_args[0]
    assert any(isinstance(a, str) and "Cote" in a for a in call_args)


@pytest.mark.asyncio
async def test_get_plan_sessions_for_week():
    rows = [
        {"id": 100, "week_id": 20, "day_of_week": 1},
        {"id": 101, "week_id": 20, "day_of_week": 3},
    ]
    pool = make_pool(fetch=rows)
    result = await get_plan_sessions_for_week(pool, week_id=20)
    assert len(result) == 2
    assert result[0]["day_of_week"] == 1


@pytest.mark.asyncio
async def test_get_plan_sessions_for_week_empty():
    pool = make_pool(fetch=[])
    result = await get_plan_sessions_for_week(pool, week_id=20)
    assert result == []


@pytest.mark.asyncio
async def test_get_plan_sessions_returns_all():
    rows = [
        {"id": 100, "plan_id": 5},
        {"id": 101, "plan_id": 5},
        {"id": 102, "plan_id": 5},
    ]
    pool = make_pool(fetch=rows)
    result = await get_plan_sessions(pool, plan_id=5)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_plan_sessions_uses_join_query():
    pool = make_pool(fetch=[])
    await get_plan_sessions(pool, plan_id=5)
    query = pool.fetch.call_args[0][0]
    assert "JOIN" in query.upper()
    assert "training_plan_weeks" in query


# ---------------------------------------------------------------------------
# Planned Workout for Session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_planned_workout_for_session_basic():
    row = {"id": 200, "user_id": 1, "plan_id": 5, "title": "EF 60min"}
    pool = make_pool(fetchrow=row)
    session_data = {
        "title": "EF 60min",
        "session_type": "EF",
        "sport_type": "trail_running",
        "intensity": "easy",
    }
    result = await create_planned_workout_for_session(
        pool, user_id=1, plan_id=5, session_data=session_data, workout_date=date(2026, 1, 5)
    )
    assert result == dict(row)
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_planned_workout_for_session_serializes_blocks():
    row = {"id": 201, "user_id": 1, "plan_id": 5, "title": "INT"}
    pool = make_pool(fetchrow=row)
    blocks = [{"name": "Interval", "duration_seconds": 240, "description": "hard"}]
    session_data = {
        "title": "INT",
        "blocks": blocks,
    }
    await create_planned_workout_for_session(
        pool, user_id=1, plan_id=5, session_data=session_data, workout_date=date(2026, 1, 7)
    )
    call_args = pool.fetchrow.call_args[0]
    assert any(isinstance(a, str) and "Interval" in a for a in call_args)


@pytest.mark.asyncio
async def test_create_planned_workout_for_session_default_sport_type():
    row = {"id": 202, "user_id": 1, "plan_id": 5, "title": "EF"}
    pool = make_pool(fetchrow=row)
    session_data = {"title": "EF"}
    await create_planned_workout_for_session(
        pool, user_id=1, plan_id=5, session_data=session_data, workout_date=date(2026, 1, 6)
    )
    call_args = pool.fetchrow.call_args[0]
    assert "trail_running" in call_args
