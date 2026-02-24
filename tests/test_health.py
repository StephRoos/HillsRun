"""Tests for health check endpoint.

Verifies:
- Endpoint returns 200 when DB is reachable
- Response contains status, version, uptime_seconds, db_connected
- DB connectivity check works (SELECT 1)
- Endpoint is public (no auth required)
- Degraded response (503) when DB is down
"""

import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.token_manager import TokenManager
from src.version import __version__


@pytest.fixture
def client():
    """FastAPI test client with environment setup."""
    os.environ["API_KEY"] = "test-health-key-12345"
    os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()
    return TestClient(app)


def _make_mock_db(fetchval_raises: bool = False) -> AsyncMock:
    """Build a mock DB suitable for health check tests.

    Args:
        fetchval_raises: If True, pool.fetchval raises an exception to simulate DB down.

    Returns:
        AsyncMock configured as a minimal Database stub.
    """
    mock_db = MagicMock()
    if fetchval_raises:
        mock_db.pool.fetchval = AsyncMock(side_effect=Exception("connection refused"))
    else:
        mock_db.pool.fetchval = AsyncMock(return_value=1)
    mock_db.query_first_user = AsyncMock(return_value=1)
    return mock_db


class TestHealthEndpointOk:
    """Health endpoint with a working DB connection."""

    def test_returns_200(self, client):
        """Health endpoint returns HTTP 200 when DB is reachable."""
        mock_db = _make_mock_db()
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        assert response.status_code == 200

    def test_status_is_ok(self, client):
        """Health response body contains status=ok."""
        mock_db = _make_mock_db()
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_contains_version(self, client):
        """Health response includes application version."""
        mock_db = _make_mock_db()
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == __version__

    def test_contains_uptime(self, client):
        """Health response includes uptime_seconds when start_time is tracked."""
        from datetime import datetime, timezone, timedelta

        mock_db = _make_mock_db()
        fake_start = datetime.now(timezone.utc) - timedelta(seconds=42)
        with (
            patch.object(app.state, "db", mock_db, create=True),
            patch.object(app.state, "start_time", fake_start, create=True),
        ):
            response = client.get("/health")
        data = response.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] is not None
        assert data["uptime_seconds"] >= 40  # at least ~42 s minus execution time

    def test_db_connected_true(self, client):
        """Health response reports db_connected=True when SELECT 1 succeeds."""
        mock_db = _make_mock_db()
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        data = response.json()
        assert data["db_connected"] is True

    def test_no_auth_required(self, client):
        """Health endpoint is accessible without any API key."""
        mock_db = _make_mock_db()
        with patch.object(app.state, "db", mock_db, create=True):
            # No X-API-Key header
            response = client.get("/health")
        assert response.status_code == 200

    def test_response_schema(self, client):
        """Health response contains all expected fields."""
        mock_db = _make_mock_db()
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "db_connected" in data


class TestHealthEndpointDegraded:
    """Health endpoint when DB connection is down."""

    def test_returns_503_when_db_down(self, client):
        """Health endpoint returns HTTP 503 when DB SELECT 1 fails."""
        mock_db = _make_mock_db(fetchval_raises=True)
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        assert response.status_code == 503

    def test_status_is_degraded_when_db_down(self, client):
        """Health response body contains status=degraded when DB is unreachable."""
        mock_db = _make_mock_db(fetchval_raises=True)
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        data = response.json()
        assert data["status"] == "degraded"

    def test_db_connected_false_when_db_down(self, client):
        """Health response reports db_connected=False when SELECT 1 fails."""
        mock_db = _make_mock_db(fetchval_raises=True)
        with patch.object(app.state, "db", mock_db, create=True):
            response = client.get("/health")
        data = response.json()
        assert data["db_connected"] is False
