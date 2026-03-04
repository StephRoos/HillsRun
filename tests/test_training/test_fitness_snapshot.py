"""Tests for the fitness snapshot builder."""

from unittest.mock import AsyncMock, patch

import pytest

from src.training.fitness_snapshot import (
    _get_activity_metrics,
    _get_avg_hrv,
    _get_avg_resting_hr,
    _get_avg_sleep_score,
    _get_recent_weight,
    _get_training_readiness,
    _get_vma,
    _get_vo2_max,
    build_fitness_snapshot,
)
from src.training.models import UserFitnessData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pool(fetchrow_return=None):
    """Create a minimal mock asyncpg pool."""
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=fetchrow_return)
    return pool


# ---------------------------------------------------------------------------
# _get_vo2_max
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vo2_max_with_data():
    row = {"vo2_max": 55.3}
    pool = make_pool(fetchrow_return=row)
    result = await _get_vo2_max(pool, user_id=1)
    assert result == 55.3


@pytest.mark.asyncio
async def test_get_vo2_max_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_vo2_max(pool, user_id=1)
    assert result is None


# ---------------------------------------------------------------------------
# _get_avg_resting_hr
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_avg_resting_hr_with_data():
    row = {"avg_rhr": 52}
    pool = make_pool(fetchrow_return=row)
    result = await _get_avg_resting_hr(pool, user_id=1)
    assert result == 52


@pytest.mark.asyncio
async def test_get_avg_resting_hr_null_avg():
    # Row exists but AVG returned NULL (no qualifying rows)
    row = {"avg_rhr": None}
    pool = make_pool(fetchrow_return=row)
    result = await _get_avg_resting_hr(pool, user_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_get_avg_resting_hr_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_avg_resting_hr(pool, user_id=1)
    assert result is None


# ---------------------------------------------------------------------------
# _get_recent_weight
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_recent_weight_with_data():
    row = {"weight_kg": 72.5}
    pool = make_pool(fetchrow_return=row)
    result = await _get_recent_weight(pool, user_id=1)
    assert result == 72.5


@pytest.mark.asyncio
async def test_get_recent_weight_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_recent_weight(pool, user_id=1)
    assert result is None


# ---------------------------------------------------------------------------
# _get_activity_metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_activity_metrics_with_data():
    row = {
        "weekly_km": 65.0,
        "weekly_elevation": 1200,
        "max_distance_km": 32.5,
        "max_duration_s": 14400,
    }
    pool = make_pool(fetchrow_return=row)
    result = await _get_activity_metrics(pool, user_id=1)
    assert result["weekly_volume_km"] == 65.0
    assert result["weekly_elevation_m"] == 1200
    assert result["recent_long_run_km"] == 32.5
    assert result["recent_long_run_duration_s"] == 14400


@pytest.mark.asyncio
async def test_get_activity_metrics_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_activity_metrics(pool, user_id=1)
    assert result == {}


@pytest.mark.asyncio
async def test_get_activity_metrics_returns_four_keys():
    row = {
        "weekly_km": 40.0,
        "weekly_elevation": 800,
        "max_distance_km": 20.0,
        "max_duration_s": 7200,
    }
    pool = make_pool(fetchrow_return=row)
    result = await _get_activity_metrics(pool, user_id=1)
    assert set(result.keys()) == {
        "weekly_volume_km",
        "weekly_elevation_m",
        "recent_long_run_km",
        "recent_long_run_duration_s",
    }


# ---------------------------------------------------------------------------
# _get_training_readiness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_training_readiness_with_data():
    row = {"avg_score": 68.5, "chronic_load": 420.0, "acute_load": 380.0}
    pool = make_pool(fetchrow_return=row)
    result = await _get_training_readiness(pool, user_id=1)
    assert result["avg_score"] == 68.5
    assert result["chronic_load"] == 420.0
    assert result["acute_load"] == 380.0


@pytest.mark.asyncio
async def test_get_training_readiness_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_training_readiness(pool, user_id=1)
    assert result == {}


# ---------------------------------------------------------------------------
# _get_vma
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vma_with_data():
    row = {"vma": 17.5}
    pool = make_pool(fetchrow_return=row)
    result = await _get_vma(pool, user_id=1)
    assert result == 17.5


@pytest.mark.asyncio
async def test_get_vma_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_vma(pool, user_id=1)
    assert result is None


# ---------------------------------------------------------------------------
# _get_avg_sleep_score
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_avg_sleep_score_with_data():
    row = {"avg_score": 74.2}
    pool = make_pool(fetchrow_return=row)
    result = await _get_avg_sleep_score(pool, user_id=1)
    assert result == 74.2


@pytest.mark.asyncio
async def test_get_avg_sleep_score_null_score():
    row = {"avg_score": None}
    pool = make_pool(fetchrow_return=row)
    result = await _get_avg_sleep_score(pool, user_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_get_avg_sleep_score_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_avg_sleep_score(pool, user_id=1)
    assert result is None


# ---------------------------------------------------------------------------
# _get_avg_hrv
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_avg_hrv_with_data():
    row = {"avg_hrv": 48.3}
    pool = make_pool(fetchrow_return=row)
    result = await _get_avg_hrv(pool, user_id=1)
    assert result == 48.3


@pytest.mark.asyncio
async def test_get_avg_hrv_null_value():
    row = {"avg_hrv": None}
    pool = make_pool(fetchrow_return=row)
    result = await _get_avg_hrv(pool, user_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_get_avg_hrv_no_row():
    pool = make_pool(fetchrow_return=None)
    result = await _get_avg_hrv(pool, user_id=1)
    assert result is None


# ---------------------------------------------------------------------------
# build_fitness_snapshot
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_fitness_snapshot_all_data():
    """Full snapshot when all helpers return data."""
    with (
        patch("src.training.fitness_snapshot._get_vo2_max", return_value=55.0),
        patch("src.training.fitness_snapshot._get_avg_resting_hr", return_value=50),
        patch("src.training.fitness_snapshot._get_recent_weight", return_value=72.0),
        patch("src.training.fitness_snapshot._get_activity_metrics", return_value={
            "weekly_volume_km": 70.0,
            "weekly_elevation_m": 1500,
            "recent_long_run_km": 35.0,
            "recent_long_run_duration_s": 15000,
        }),
        patch("src.training.fitness_snapshot._get_training_readiness", return_value={
            "avg_score": 72.0,
            "chronic_load": 450.0,
            "acute_load": 400.0,
        }),
        patch("src.training.fitness_snapshot._get_vma", return_value=18.0),
        patch("src.training.fitness_snapshot._get_avg_sleep_score", return_value=80.0),
        patch("src.training.fitness_snapshot._get_avg_hrv", return_value=50.0),
    ):
        pool = AsyncMock()
        result = await build_fitness_snapshot(pool, user_id=1)

    assert isinstance(result, UserFitnessData)
    assert result.vo2_max == 55.0
    assert result.resting_hr == 50
    assert result.weight_kg == 72.0
    assert result.vma_kmh == 18.0
    assert result.weekly_volume_km == 70.0
    assert result.weekly_elevation_m == 1500
    assert result.recent_long_run_km == 35.0
    assert result.recent_long_run_duration_s == 15000
    assert result.avg_training_readiness == 72.0
    assert result.chronic_load == 450.0
    assert result.acute_load == 400.0
    assert result.avg_sleep_score == 80.0
    assert result.avg_hrv == 50.0


@pytest.mark.asyncio
async def test_build_fitness_snapshot_no_data():
    """Snapshot with all None when all helpers return nothing."""
    with (
        patch("src.training.fitness_snapshot._get_vo2_max", return_value=None),
        patch("src.training.fitness_snapshot._get_avg_resting_hr", return_value=None),
        patch("src.training.fitness_snapshot._get_recent_weight", return_value=None),
        patch("src.training.fitness_snapshot._get_activity_metrics", return_value={}),
        patch("src.training.fitness_snapshot._get_training_readiness", return_value={}),
        patch("src.training.fitness_snapshot._get_vma", return_value=None),
        patch("src.training.fitness_snapshot._get_avg_sleep_score", return_value=None),
        patch("src.training.fitness_snapshot._get_avg_hrv", return_value=None),
    ):
        pool = AsyncMock()
        result = await build_fitness_snapshot(pool, user_id=1)

    assert isinstance(result, UserFitnessData)
    assert result.vo2_max is None
    assert result.resting_hr is None
    assert result.weight_kg is None
    assert result.vma_kmh is None
    assert result.weekly_volume_km is None
    assert result.weekly_elevation_m is None
    assert result.recent_long_run_km is None
    assert result.recent_long_run_duration_s is None
    assert result.avg_training_readiness is None
    assert result.chronic_load is None
    assert result.acute_load is None
    assert result.avg_sleep_score is None
    assert result.avg_hrv is None


@pytest.mark.asyncio
async def test_build_fitness_snapshot_partial_data():
    """Snapshot with some helpers returning data and others returning None."""
    with (
        patch("src.training.fitness_snapshot._get_vo2_max", return_value=52.0),
        patch("src.training.fitness_snapshot._get_avg_resting_hr", return_value=None),
        patch("src.training.fitness_snapshot._get_recent_weight", return_value=75.0),
        patch("src.training.fitness_snapshot._get_activity_metrics", return_value={
            "weekly_volume_km": 50.0,
            "weekly_elevation_m": None,
            "recent_long_run_km": 25.0,
            "recent_long_run_duration_s": None,
        }),
        patch("src.training.fitness_snapshot._get_training_readiness", return_value={}),
        patch("src.training.fitness_snapshot._get_vma", return_value=16.5),
        patch("src.training.fitness_snapshot._get_avg_sleep_score", return_value=None),
        patch("src.training.fitness_snapshot._get_avg_hrv", return_value=45.0),
    ):
        pool = AsyncMock()
        result = await build_fitness_snapshot(pool, user_id=1)

    assert result.vo2_max == 52.0
    assert result.resting_hr is None
    assert result.weight_kg == 75.0
    assert result.vma_kmh == 16.5
    assert result.weekly_volume_km == 50.0
    assert result.weekly_elevation_m is None
    assert result.avg_training_readiness is None
    assert result.avg_hrv == 45.0
