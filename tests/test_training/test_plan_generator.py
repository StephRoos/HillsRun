"""Integration tests for plan generator (uses mock DB)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from src.training.plan_generator import generate_plan
from src.training.models import GeneratePlanRequest


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
