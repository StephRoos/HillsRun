"""Integration tests for plan generator (uses mock DB)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from src.training.plan_generator import generate_plan, _resolve_available_days, _resolve_day_preferences
from src.training.models import DayPreferences, GeneratePlanRequest


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    pool = AsyncMock()

    # Mock connection context
    conn = AsyncMock()
    tx = AsyncMock()
    tx.__aenter__ = AsyncMock(return_value=tx)
    tx.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=tx)

    # conn.fetchrow returns mock rows
    plan_row = {"id": 1, "name": "Test Plan"}
    week_row = {"id": 1}
    session_row = {"id": 1}
    pw_row = {"id": 1}
    conn.fetchrow = AsyncMock(side_effect=[plan_row] + [week_row, pw_row, session_row] * 100)

    # Pool.acquire context
    pool_cm = AsyncMock()
    pool_cm.__aenter__ = AsyncMock(return_value=conn)
    pool_cm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=pool_cm)

    return pool


@pytest.fixture
def mock_profile():
    return {
        "user_id": 67,
        "experience_level": "intermediate",
        "fc_max": 185,
        "fc_repos": 55,
        "available_days_per_week": 4,
        "birth_date": date(1990, 5, 15),
    }


@pytest.fixture
def mock_race():
    return {
        "id": 1,
        "race_name": "Trail des Aiguilles Rouges",
        "race_date": date(2026, 9, 15),
        "distance_km": 55,
        "elevation_gain_m": 3500,
        "elevation_loss_m": 3500,
        "technical_percent": 20,
        "altitude_max_m": 2600,
        "objective": "midpack",
    }


@pytest.mark.asyncio
async def test_generate_plan_creates_plan(mock_pool, mock_profile, mock_race):
    """Test that generate_plan produces a plan with correct structure."""
    request = GeneratePlanRequest(
        race_target_id=1,
        plan_name="Test Training Plan",
        total_weeks=12,
        start_date=date(2026, 6, 22),
    )

    with patch("src.training.plan_generator.build_fitness_snapshot") as mock_fitness, \
         patch("src.training.plan_generator.db_ops") as mock_db:

        from src.training.models import UserFitnessData
        mock_fitness.return_value = UserFitnessData(
            vo2_max=48.0, resting_hr=55, max_hr=185,
            weight_kg=72.0, vma_kmh=15.0,
            weekly_volume_km=35.0, weekly_elevation_m=800,
            recent_long_run_km=18.0,
        )
        mock_db.get_athlete_profile = AsyncMock(return_value=mock_profile)
        mock_db.get_race_target = AsyncMock(return_value=mock_race)

        result = await generate_plan(mock_pool, 67, request)

    assert "plan_id" in result
    assert result["total_weeks"] == 12
    assert result["status"] == "draft"


@pytest.fixture
def mock_road_race():
    """Flat road marathon (Brugge) with a 3h30 target."""
    return {
        "id": 2,
        "race_name": "Marathon de Brugge",
        "race_date": date(2026, 10, 12),
        "distance_km": 42.195,
        "elevation_gain_m": 0,
        "elevation_loss_m": 0,
        "technical_percent": 0,
        "altitude_max_m": 0,
        "objective": "performance",
        "discipline": "road",
        "target_time_seconds": 12600,
    }


@pytest.mark.asyncio
async def test_generate_plan_road_marathon(mock_pool, mock_profile, mock_road_race):
    """Road marathon plan: road_running sport_type and paces stored, no D+ on LR."""
    request = GeneratePlanRequest(
        race_target_id=2,
        plan_name="Brugge 3h30",
        total_weeks=16,
        start_date=date(2026, 6, 22),
    )

    with patch("src.training.plan_generator.build_fitness_snapshot") as mock_fitness, \
         patch("src.training.plan_generator.db_ops") as mock_db:

        from src.training.models import UserFitnessData
        mock_fitness.return_value = UserFitnessData(
            vo2_max=52.0, resting_hr=56, max_hr=188,
            weight_kg=70.0, vma_kmh=14.5,
            weekly_volume_km=45.0, weekly_elevation_m=200,
            recent_long_run_km=18.0,
        )
        mock_db.get_athlete_profile = AsyncMock(return_value=mock_profile)
        mock_db.get_race_target = AsyncMock(return_value=mock_road_race)

        result = await generate_plan(mock_pool, 67, request)

    assert result["race_category"] == "road_marathon"

    # Inspect the dual-write inserts: running sessions must be road_running.
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    pw_sport_types = [
        call.args[3]
        for call in conn.fetchrow.call_args_list
        if call.args and "INSERT INTO planned_workouts" in call.args[0]
    ]
    assert pw_sport_types, "expected planned_workouts inserts"
    assert "road_running" in pw_sport_types
    assert "trail_running" not in pw_sport_types

    # Paces must be persisted in generation_params on the master plan insert.
    import json as _json
    plan_call = next(
        call
        for call in conn.fetchrow.call_args_list
        if call.args and "INSERT INTO training_plans" in call.args[0]
    )
    gen_params = _json.loads(plan_call.args[9])
    assert gen_params["discipline"] == "road"
    assert gen_params["paces"] is not None
    assert gen_params["paces"]["pace_source"] == "vma"
    assert "MPR" in gen_params["paces"]["zones"]


@pytest.mark.asyncio
async def test_generate_plan_no_profile(mock_pool):
    """Test error when no athlete profile exists."""
    request = GeneratePlanRequest(race_target_id=1, total_weeks=12)

    with patch("src.training.plan_generator.build_fitness_snapshot") as mock_fitness, \
         patch("src.training.plan_generator.db_ops") as mock_db:

        from src.training.models import UserFitnessData
        mock_fitness.return_value = UserFitnessData()
        mock_db.get_athlete_profile = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="profile"):
            await generate_plan(mock_pool, 67, request)


@pytest.mark.asyncio
async def test_generate_plan_no_race(mock_pool, mock_profile):
    """Test error when race target not found."""
    request = GeneratePlanRequest(race_target_id=999, total_weeks=12)

    with patch("src.training.plan_generator.build_fitness_snapshot") as mock_fitness, \
         patch("src.training.plan_generator.db_ops") as mock_db:

        from src.training.models import UserFitnessData
        mock_fitness.return_value = UserFitnessData()
        mock_db.get_athlete_profile = AsyncMock(return_value=mock_profile)
        mock_db.get_race_target = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Race target"):
            await generate_plan(mock_pool, 67, request)


# --- _resolve_available_days tests ---

def test_resolve_available_days_from_slots():
    """available_slots JSONB should take priority over integer."""
    profile = {
        "available_days_per_week": 3,
        "available_slots": {
            "monday": ["morning"],
            "wednesday": ["evening"],
            "friday": ["morning", "evening"],
            "saturday": ["morning"],
        },
    }
    days = _resolve_available_days(profile)
    assert days == [1, 3, 5, 6]


def test_resolve_available_days_from_slots_french():
    """French day names should work."""
    profile = {
        "available_days_per_week": 2,
        "available_slots": {
            "mardi": ["matin"],
            "samedi": ["matin"],
            "dimanche": ["matin"],
        },
    }
    days = _resolve_available_days(profile)
    assert days == [2, 6, 7]


def test_resolve_available_days_empty_slots_fallback():
    """Empty available_slots should fall back to integer."""
    profile = {"available_days_per_week": 3, "available_slots": {}}
    days = _resolve_available_days(profile)
    assert days == [2, 5, 6]  # 3-day heuristic


def test_resolve_available_days_no_slots():
    """No available_slots should use integer heuristic."""
    profile = {"available_days_per_week": 4}
    days = _resolve_available_days(profile)
    assert days == [2, 4, 6, 7]


def test_resolve_available_days_ignores_empty_slot_lists():
    """Days with empty slot lists should be excluded."""
    profile = {
        "available_slots": {
            "monday": ["morning"],
            "tuesday": [],  # Empty — should be excluded
            "saturday": ["morning"],
        },
    }
    days = _resolve_available_days(profile)
    assert days == [1, 6]


# --- _resolve_day_preferences tests ---

def test_resolve_day_preferences_override_wins():
    """Request override should take priority over profile preferences."""
    profile = {"day_preferences": {"long_run": 6, "quality": [2, 4]}}
    override = DayPreferences(long_run=7, quality=[3, 5])
    result = _resolve_day_preferences(profile, override)
    assert result is override
    assert result.long_run == 7
    assert result.quality == [3, 5]


def test_resolve_day_preferences_from_profile():
    """Profile day_preferences should be used when no override."""
    profile = {"day_preferences": {"long_run": 7, "strength": [3]}}
    result = _resolve_day_preferences(profile, None)
    assert result is not None
    assert result.long_run == 7
    assert result.strength == [3]


def test_resolve_day_preferences_none():
    """No preferences anywhere should return None."""
    profile = {"experience_level": "intermediate"}
    result = _resolve_day_preferences(profile, None)
    assert result is None
