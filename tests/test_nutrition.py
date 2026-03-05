"""Integration tests for the /api/v1/nutrition/daily-goal endpoint.

Auth model: X-API-Key (service key) + X-Better-Auth-User-Id (user identity).
The endpoint resolves the Better-Auth user ID to a Garmin user_id via DB lookup.
"""

import os
import pytest
from datetime import date
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.api.main import app
from src.token_manager import TokenManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_API_KEY = "nutrition-test-api-key-2026"
TEST_BETTER_AUTH_ID = "ba-user-abc-123"
TEST_USER_ID = 42


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_env():
    """Set required env vars for all tests in this module."""
    os.environ["API_KEY"] = TEST_API_KEY
    os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()
    yield


@pytest.fixture
def valid_headers():
    """Valid request headers with API key and Better-Auth user ID."""
    return {
        "X-API-Key": TEST_API_KEY,
        "X-Better-Auth-User-Id": TEST_BETTER_AUTH_ID,
    }


@pytest.fixture
def mock_db():
    """Mock database instance attached to app.state."""
    db = AsyncMock()
    db.query_first_user = AsyncMock(return_value=TEST_USER_ID)
    # Better-Auth → Garmin user mapping
    db.get_user_by_better_auth_id = AsyncMock(return_value=TEST_USER_ID)
    db.query_nutrition_goal = AsyncMock(return_value=None)
    return db


@pytest.fixture
def client(mock_db):
    """TestClient with mocked DB injected into app.state."""
    app.state.db = mock_db
    app.state.user_id = TEST_USER_ID
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestNutritionAuthentication:
    """Test authentication enforcement on nutrition endpoint."""

    def test_missing_api_key_returns_401(self, client):
        """Request without API key should be rejected with 401."""
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            headers={"X-Better-Auth-User-Id": TEST_BETTER_AUTH_ID},
        )
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, client):
        """Request with wrong API key should be rejected with 401."""
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            headers={
                "X-API-Key": "totally-wrong-key",
                "X-Better-Auth-User-Id": TEST_BETTER_AUTH_ID,
            },
        )
        assert response.status_code == 401

    def test_missing_better_auth_user_id_returns_401(self, client):
        """Request without X-Better-Auth-User-Id header should return 401."""
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# No Garmin account linked → 404
# ---------------------------------------------------------------------------


class TestNutritionNoGarminAccount:
    """Test 404 when no Garmin account is linked to the Better-Auth user."""

    def test_no_garmin_account_returns_404(self, client, valid_headers, mock_db):
        """Endpoint returns 404 when Better-Auth user has no linked Garmin account."""
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=None)
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-01"},
            headers=valid_headers,
        )
        assert response.status_code == 404
        assert "Garmin" in response.json()["detail"]


# ---------------------------------------------------------------------------
# No data / 204 cases
# ---------------------------------------------------------------------------


class TestNutritionNoData:
    """Test endpoint behaviour when no Garmin data is available for the date."""

    def test_no_garmin_data_returns_204(self, client, valid_headers, mock_db):
        """Endpoint returns 204 when DB has no daily summary for requested date."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=None)
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-01"},
            headers=valid_headers,
        )
        assert response.status_code == 204


# ---------------------------------------------------------------------------
# Full-data response tests
# ---------------------------------------------------------------------------


def _make_full_data() -> dict:
    return {
        "calendar_date": date(2024, 6, 15),
        "bmr_calories": 1800,
        "active_calories": 600,
        "activity_type": "running",
        "duration_seconds": 3600.0,
        "training_stress_score": 85.0,
    }


class TestNutritionFullData:
    """Test endpoint with complete BMR + active calories + activity data."""

    def test_full_data_returns_200(self, client, valid_headers, mock_db):
        """Full daily data returns 200 with all calorie fields populated."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=_make_full_data())
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-15"},
            headers=valid_headers,
        )
        assert response.status_code == 200

    def test_full_data_calorie_calculation(self, client, valid_headers, mock_db):
        """recommended_daily_intake = BMR + active_calories * 1.1."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=_make_full_data())
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-15"},
            headers=valid_headers,
        )
        body = response.json()
        assert body["base_bmr_calories"] == 1800
        assert body["active_calories"] == 600
        # active * 1.1 = 660
        assert body["total_training_calories"] == int(600 * 1.1)
        assert body["recommended_daily_intake"] == 1800 + int(600 * 1.1)

    def test_adjustment_factor_is_1_1(self, client, valid_headers, mock_db):
        """adjustment_factor is 1.1 when both BMR and active calories are present."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=_make_full_data())
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-15"},
            headers=valid_headers,
        )
        body = response.json()
        assert body["adjustment_factor"] == pytest.approx(1.1)

    def test_training_load_populated(self, client, valid_headers, mock_db):
        """training_load block is populated from activity data."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=_make_full_data())
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-15"},
            headers=valid_headers,
        )
        body = response.json()
        tl = body["training_load"]
        assert tl is not None
        assert tl["tss"] == pytest.approx(85.0)
        assert tl["duration_minutes"] == 60
        assert tl["activity_type"] == "running"

    def test_date_field_matches_request(self, client, valid_headers, mock_db):
        """Returned date matches the queried date."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=_make_full_data())
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-15"},
            headers=valid_headers,
        )
        body = response.json()
        assert body["date"] == "2024-06-15"


# ---------------------------------------------------------------------------
# Partial data tests
# ---------------------------------------------------------------------------


class TestNutritionPartialData:
    """Test endpoint with partial data (BMR only, no activity)."""

    def _make_bmr_only_data(self) -> dict:
        return {
            "calendar_date": date(2024, 6, 10),
            "bmr_calories": 1750,
            "active_calories": None,
            "activity_type": None,
            "duration_seconds": None,
            "training_stress_score": None,
        }

    def test_bmr_only_returns_200(self, client, valid_headers, mock_db):
        """BMR-only data (rest day) returns 200."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=self._make_bmr_only_data())
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-10"},
            headers=valid_headers,
        )
        assert response.status_code == 200

    def test_bmr_only_recommended_equals_bmr(self, client, valid_headers, mock_db):
        """Without active calories, recommended = BMR and no adjustment_factor."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=self._make_bmr_only_data())
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2024-06-10"},
            headers=valid_headers,
        )
        body = response.json()
        assert body["base_bmr_calories"] == 1750
        assert body["active_calories"] is None
        assert body["recommended_daily_intake"] == 1750
        assert body["adjustment_factor"] is None
        assert body["training_load"] is None


# ---------------------------------------------------------------------------
# Date parameter tests
# ---------------------------------------------------------------------------


class TestNutritionDateParam:
    """Test date query parameter handling."""

    def test_invalid_date_format_returns_422(self, client, valid_headers):
        """Invalid date format should return 422 Unprocessable Entity."""
        response = client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "not-a-date"},
            headers=valid_headers,
        )
        assert response.status_code == 422

    def test_default_date_is_today(self, client, valid_headers, mock_db):
        """Omitting the date param calls DB with today's date."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=None)
        client.get("/api/v1/nutrition/daily-goal", headers=valid_headers)
        called_date = mock_db.query_nutrition_goal.call_args.args[1]
        assert called_date == date.today()

    def test_explicit_date_forwarded_to_db(self, client, valid_headers, mock_db):
        """Explicit date param is correctly forwarded to the DB query."""
        mock_db.query_nutrition_goal = AsyncMock(return_value=None)
        client.get(
            "/api/v1/nutrition/daily-goal",
            params={"date": "2025-01-20"},
            headers=valid_headers,
        )
        called_date = mock_db.query_nutrition_goal.call_args.args[1]
        assert called_date == date(2025, 1, 20)
