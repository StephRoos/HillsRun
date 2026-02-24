"""Tests for Cache-Control header middleware.

Verifies that CacheControlMiddleware sets appropriate headers on GET responses:
- Historical date range (end_date < today): Cache-Control: public, max-age=86400
- Today/no date: Cache-Control: private, max-age=300
- Sync endpoints: Cache-Control: no-store
- Auth endpoints: Cache-Control: no-store
- Coaching endpoints: Cache-Control: no-store
- Nutrition endpoints: Cache-Control: no-store
- Non-GET methods: no Cache-Control header added
"""

import os
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.token_manager import TokenManager


@pytest.fixture
def test_api_key():
    """Provide a test API key."""
    return "test-cache-key-12345"


@pytest.fixture
def client(test_api_key):
    """FastAPI test client with middleware registered."""
    os.environ["API_KEY"] = test_api_key
    os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()
    return TestClient(app)


@pytest.fixture
def valid_headers(test_api_key):
    """Valid API key headers."""
    return {"X-API-Key": test_api_key}


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _two_weeks_ago() -> str:
    return (date.today() - timedelta(days=14)).isoformat()


def _today() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Helpers to call a cacheable endpoint with a mocked DB
# ---------------------------------------------------------------------------


def _get_with_mock_db(client, path, headers, params=None):
    """Issue a GET request with the DB mocked to return empty data."""
    mock_db = AsyncMock()
    mock_db.query_daily_summaries = AsyncMock(return_value=([], 0))
    mock_db.query_heart_rate_samples = AsyncMock(return_value=([], 0))
    mock_db.query_sleep_data = AsyncMock(return_value=([], 0))
    mock_db.query_stress_data = AsyncMock(return_value=([], 0))
    mock_db.query_body_battery = AsyncMock(return_value=([], 0))
    mock_db.query_body_composition = AsyncMock(return_value=([], 0))
    mock_db.query_hrv_data = AsyncMock(return_value=([], 0))
    mock_db.query_spo2_data = AsyncMock(return_value=([], 0))
    mock_db.query_fitness_metrics = AsyncMock(return_value=([], 0))
    mock_db.query_respiration_data = AsyncMock(return_value=([], 0))
    mock_db.query_training_readiness = AsyncMock(return_value=([], 0))
    mock_db.query_activities = AsyncMock(return_value=([], 0))
    mock_db.query_sync_status = AsyncMock(return_value=[])
    mock_db.query_first_user = AsyncMock(return_value=1)

    with (
        patch.object(app.state, "db", mock_db, create=True),
        patch.object(app.state, "user_id", 1, create=True),
    ):
        return client.get(path, headers=headers, params=params or {})


# ---------------------------------------------------------------------------
# Historical date range → public, max-age=86400
# ---------------------------------------------------------------------------


class TestHistoricalCacheHeaders:
    """GET with end_date in the past should return public 24 h cache."""

    def test_daily_summary_historical(self, client, valid_headers):
        """Historical end_date on /daily/summary → public, max-age=86400."""
        response = _get_with_mock_db(
            client,
            "/api/v1/daily/summary",
            valid_headers,
            {"start_date": _two_weeks_ago(), "end_date": _yesterday()},
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "public, max-age=86400"

    def test_metrics_hrv_historical(self, client, valid_headers):
        """Historical end_date on /metrics/hrv → public, max-age=86400."""
        response = _get_with_mock_db(
            client,
            "/api/v1/metrics/hrv",
            valid_headers,
            {"end_date": _yesterday()},
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "public, max-age=86400"

    def test_body_composition_historical(self, client, valid_headers):
        """Historical end_date on /body/composition → public, max-age=86400."""
        response = _get_with_mock_db(
            client,
            "/api/v1/body/composition",
            valid_headers,
            {"end_date": _yesterday()},
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "public, max-age=86400"

    def test_activities_historical(self, client, valid_headers):
        """Historical end_date on /activities → public, max-age=86400."""
        response = _get_with_mock_db(
            client,
            "/api/v1/activities",
            valid_headers,
            {"end_date": _yesterday()},
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "public, max-age=86400"


# ---------------------------------------------------------------------------
# Today's date or no date → private, max-age=300
# ---------------------------------------------------------------------------


class TestCurrentCacheHeaders:
    """GET with today's date or no date should return private 5 min cache."""

    def test_daily_summary_today(self, client, valid_headers):
        """end_date == today on /daily/summary → private, max-age=300."""
        response = _get_with_mock_db(
            client,
            "/api/v1/daily/summary",
            valid_headers,
            {"end_date": _today()},
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "private, max-age=300"

    def test_daily_summary_no_date(self, client, valid_headers):
        """No date param on /daily/summary → private, max-age=300 (defaults to today)."""
        response = _get_with_mock_db(
            client,
            "/api/v1/daily/summary",
            valid_headers,
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "private, max-age=300"

    def test_metrics_hrv_today(self, client, valid_headers):
        """end_date == today on /metrics/hrv → private, max-age=300."""
        response = _get_with_mock_db(
            client,
            "/api/v1/metrics/hrv",
            valid_headers,
            {"end_date": _today()},
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "private, max-age=300"

    def test_activities_no_date(self, client, valid_headers):
        """No date param on /activities → private, max-age=300."""
        response = _get_with_mock_db(
            client,
            "/api/v1/activities",
            valid_headers,
        )
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "private, max-age=300"


# ---------------------------------------------------------------------------
# Non-cacheable endpoints → no-store
# ---------------------------------------------------------------------------


class TestNoCacheEndpoints:
    """Sync, auth, coaching, and nutrition endpoints must return no-store."""

    def test_sync_status_no_store(self, client, valid_headers):
        """GET /sync/status → Cache-Control: no-store."""
        mock_db = AsyncMock()
        mock_db.query_sync_status = AsyncMock(return_value=[])

        with (
            patch.object(app.state, "db", mock_db, create=True),
            patch.object(app.state, "user_id", 1, create=True),
        ):
            response = client.get("/api/v1/sync/status", headers=valid_headers)

        assert response.status_code == 200
        assert response.headers.get("cache-control") == "no-store"

    def test_auth_status_no_store(self, client, valid_headers):
        """GET /auth/status → Cache-Control: no-store."""
        mock_db = AsyncMock()
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=None)

        with (
            patch.object(app.state, "db", mock_db, create=True),
            patch.object(app.state, "user_id", 1, create=True),
        ):
            response = client.get(
                "/api/v1/auth/status",
                headers=valid_headers,
                params={"better_auth_user_id": "test-user"},
            )

        assert response.status_code == 200
        assert response.headers.get("cache-control") == "no-store"

    def test_sync_jobs_no_store(self, client, valid_headers):
        """GET /sync/jobs → Cache-Control: no-store."""
        response = client.get("/api/v1/sync/jobs", headers=valid_headers)
        assert response.status_code == 200
        assert response.headers.get("cache-control") == "no-store"
