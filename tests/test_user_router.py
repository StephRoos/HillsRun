"""Tests for /api/v1/user/vma endpoints."""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.token_manager import TokenManager


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_API_KEY = "user-router-test-api-key-9999"
TEST_USER_ID = 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_env():
    """Set required environment variables for all tests in this module."""
    os.environ["API_KEY"] = TEST_API_KEY
    os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()
    yield


@pytest.fixture
def valid_headers():
    """Valid API request headers."""
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def mock_db():
    """Mock database with default VMA-related method stubs."""
    db = AsyncMock()
    db.get_user_vma = AsyncMock(return_value=None)
    db.get_latest_vo2max_running = AsyncMock(return_value=None)
    db.update_user_vma = AsyncMock(return_value=None)
    db.query_first_user = AsyncMock(return_value=TEST_USER_ID)
    return db


@pytest.fixture
def client(mock_db):
    """TestClient with mocked DB injected into app.state."""
    app.state.db = mock_db
    app.state.user_id = TEST_USER_ID
    app.state.start_time = datetime.now(timezone.utc)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /api/v1/user/vma
# ---------------------------------------------------------------------------


class TestGetVma:
    """Tests for GET /api/v1/user/vma."""

    def test_get_vma_returns_manual_vma(self, client, valid_headers, mock_db):
        """GET /vma returns manual_vma when set in DB."""
        mock_db.get_user_vma = AsyncMock(return_value=17.5)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=None)

        response = client.get("/api/v1/user/vma", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["manual_vma"] == 17.5

    def test_get_vma_returns_estimated_vma_from_vo2max(self, client, valid_headers, mock_db):
        """GET /vma returns estimated_vma computed from vo2max (vo2max / 3.5)."""
        mock_db.get_user_vma = AsyncMock(return_value=None)
        # 52.5 / 3.5 = 15.0
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=52.5)

        response = client.get("/api/v1/user/vma", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["estimated_vma"] == 15.0

    def test_get_vma_returns_vo2_max(self, client, valid_headers, mock_db):
        """GET /vma exposes the raw vo2_max value."""
        mock_db.get_user_vma = AsyncMock(return_value=None)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=48.3)

        response = client.get("/api/v1/user/vma", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["vo2_max"] == 48.3

    def test_get_vma_with_no_data_returns_nulls(self, client, valid_headers, mock_db):
        """GET /vma returns all null fields when no VMA data exists."""
        mock_db.get_user_vma = AsyncMock(return_value=None)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=None)

        response = client.get("/api/v1/user/vma", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["manual_vma"] is None
        assert body["estimated_vma"] is None
        assert body["vo2_max"] is None

    def test_get_vma_estimated_vma_rounded_to_2_decimals(self, client, valid_headers, mock_db):
        """estimated_vma is rounded to 2 decimal places."""
        mock_db.get_user_vma = AsyncMock(return_value=None)
        # 50.0 / 3.5 = 14.285714... → 14.29
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=50.0)

        response = client.get("/api/v1/user/vma", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["estimated_vma"] == 14.29

    def test_get_vma_returns_all_three_fields(self, client, valid_headers, mock_db):
        """GET /vma response includes manual_vma, estimated_vma and vo2_max keys."""
        response = client.get("/api/v1/user/vma", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert "manual_vma" in body
        assert "estimated_vma" in body
        assert "vo2_max" in body

    def test_get_vma_without_api_key_returns_401(self, client):
        """GET /vma without API key returns 401."""
        response = client.get("/api/v1/user/vma")
        assert response.status_code == 401

    def test_get_vma_with_invalid_api_key_returns_401(self, client):
        """GET /vma with wrong API key returns 401."""
        response = client.get(
            "/api/v1/user/vma",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_get_vma_both_manual_and_estimated_present(self, client, valid_headers, mock_db):
        """GET /vma can return both manual_vma and estimated_vma simultaneously."""
        mock_db.get_user_vma = AsyncMock(return_value=18.0)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=52.5)

        response = client.get("/api/v1/user/vma", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["manual_vma"] == 18.0
        assert body["estimated_vma"] == 15.0
        assert body["vo2_max"] == 52.5


# ---------------------------------------------------------------------------
# PATCH /api/v1/user/vma
# ---------------------------------------------------------------------------


class TestPatchVma:
    """Tests for PATCH /api/v1/user/vma."""

    def test_patch_vma_updates_manual_vma(self, client, valid_headers, mock_db):
        """PATCH /vma with valid value calls update_user_vma."""
        mock_db.update_user_vma = AsyncMock(return_value=None)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=None)

        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 17.5},
            headers=valid_headers,
        )

        assert response.status_code == 200
        mock_db.update_user_vma.assert_called_once_with(TEST_USER_ID, 17.5)

    def test_patch_vma_returns_updated_manual_vma(self, client, valid_headers, mock_db):
        """PATCH /vma returns the new manual_vma in the response."""
        mock_db.update_user_vma = AsyncMock(return_value=None)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=None)

        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 16.0},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["manual_vma"] == 16.0

    def test_patch_vma_with_null_clears_vma(self, client, valid_headers, mock_db):
        """PATCH /vma with null clears the manual VMA (calls update with None)."""
        mock_db.update_user_vma = AsyncMock(return_value=None)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=None)

        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": None},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["manual_vma"] is None
        mock_db.update_user_vma.assert_called_once_with(TEST_USER_ID, None)

    def test_patch_vma_below_minimum_returns_422(self, client, valid_headers):
        """PATCH /vma with value < 5 returns 422 validation error."""
        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 4.9},
            headers=valid_headers,
        )
        assert response.status_code == 422

    def test_patch_vma_above_maximum_returns_422(self, client, valid_headers):
        """PATCH /vma with value > 30 returns 422 validation error."""
        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 30.1},
            headers=valid_headers,
        )
        assert response.status_code == 422

    def test_patch_vma_at_minimum_boundary_accepted(self, client, valid_headers, mock_db):
        """PATCH /vma with value == 5 (lower boundary) is accepted."""
        mock_db.update_user_vma = AsyncMock(return_value=None)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=None)

        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 5.0},
            headers=valid_headers,
        )
        assert response.status_code == 200

    def test_patch_vma_at_maximum_boundary_accepted(self, client, valid_headers, mock_db):
        """PATCH /vma with value == 30 (upper boundary) is accepted."""
        mock_db.update_user_vma = AsyncMock(return_value=None)
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=None)

        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 30.0},
            headers=valid_headers,
        )
        assert response.status_code == 200

    def test_patch_vma_without_api_key_returns_401(self, client):
        """PATCH /vma without API key returns 401."""
        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 17.0},
        )
        assert response.status_code == 401

    def test_patch_vma_includes_estimated_vma_in_response(self, client, valid_headers, mock_db):
        """PATCH /vma response also returns estimated_vma when vo2max is available."""
        mock_db.update_user_vma = AsyncMock(return_value=None)
        # 49.0 / 3.5 = 14.0
        mock_db.get_latest_vo2max_running = AsyncMock(return_value=49.0)

        response = client.patch(
            "/api/v1/user/vma",
            json={"vma": 15.0},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["manual_vma"] == 15.0
        assert body["estimated_vma"] == 14.0
        assert body["vo2_max"] == 49.0
