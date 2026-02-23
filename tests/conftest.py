"""Fixtures and configuration for pytest."""

import os
import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from fastapi.testclient import TestClient

from src.config import Config, DatabaseConfig, GarminConfig, SyncConfig, LoggingConfig
from src.database import Database
from src.garmin_client import GarminClient
from src.token_manager import TokenManager
from src.api.main import app


@pytest.fixture
def test_token_key():
    """Generate a test Fernet key for token encryption."""
    return TokenManager.generate_key()


@pytest.fixture
def test_db_config():
    """Provide test database configuration."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_garmin",
        user="test_user",
        password="test_password",
        pool_min_size=1,
        pool_max_size=5,
    )


@pytest.fixture
def test_garmin_config(tmp_path):
    """Provide test Garmin configuration."""
    tokens_dir = tmp_path / "garmin_tokens"
    tokens_dir.mkdir(exist_ok=True)
    return GarminConfig(
        tokens_dir=tokens_dir,
        email="test@garmin.com",
        password="test_password",
        token_key=TokenManager.generate_key(),
    )


@pytest.fixture
def test_config(test_db_config, test_garmin_config):
    """Provide test application configuration."""
    return Config(
        database=test_db_config,
        garmin=test_garmin_config,
        sync=SyncConfig(),
        logging=LoggingConfig(),
    )


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg connection pool."""
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value=None)
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value=None)
    pool.close = AsyncMock()
    return pool


@pytest_asyncio.fixture
async def mock_database(mock_db_pool, test_db_config):
    """Provide a mocked Database instance."""
    db = Database(test_db_config)
    db.pool = mock_db_pool
    return db


@pytest.fixture
def mock_garmin_client():
    """Mock GarminClient for testing."""
    client = MagicMock(spec=GarminClient)
    client.get_user_profile = MagicMock(return_value=(True, {"displayName": "Test User"}, None))
    client.get_user_summary = MagicMock(return_value=(True, {"totalSteps": 10000}, None))
    client.get_heart_rates = MagicMock(return_value=(True, {"heartRateValues": []}, None))
    client.get_sleep_data = MagicMock(return_value=(True, {"dailySleepDTO": {}}, None))
    client.get_stress_data = MagicMock(return_value=(True, {}, None))
    client.get_body_battery = MagicMock(return_value=(True, {}, None))
    client.get_weigh_ins = MagicMock(return_value=(True, [], None))
    client.get_body_composition = MagicMock(return_value=(True, {}, None))
    client.get_hrv_data = MagicMock(return_value=(True, {}, None))
    client.get_spo2_data = MagicMock(return_value=(True, {}, None))
    client.get_max_metrics = MagicMock(return_value=(True, {}, None))
    client.get_respiration_data = MagicMock(return_value=(True, {}, None))
    client.get_training_readiness = MagicMock(return_value=(True, {}, None))
    client.get_activities_by_date = MagicMock(return_value=(True, [], None))
    client.get_activity = MagicMock(return_value=(True, {}, None))
    client.get_activity_splits = MagicMock(return_value=(True, {}, None))
    client.get_hydration_data = MagicMock(return_value=(True, {}, None))
    return client


@pytest.fixture
def test_api_key():
    """Provide a test API key."""
    return "test-api-key-12345"


@pytest.fixture
def api_client(test_api_key):
    """Provide a FastAPI TestClient with mocked DB."""
    # Set required environment variables
    os.environ["API_KEY"] = test_api_key
    os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()

    client = TestClient(app)
    return client


@pytest.fixture
def valid_headers(test_api_key):
    """Provide valid API headers for requests."""
    return {
        "X-API-Key": test_api_key,
    }


@pytest.fixture
def invalid_headers():
    """Provide invalid API headers for requests."""
    return {
        "X-API-Key": "invalid-key",
    }
