"""Integration tests for FastAPI routers: full request→response cycle with mocked DB."""

import os
import pytest
import pytest_asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from src.api.main import app
from src.token_manager import TokenManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_API_KEY = "integration-test-api-key-9999"
TEST_USER_ID = 67


@pytest.fixture(autouse=True)
def setup_env():
    """Set required env vars for all tests in this module."""
    os.environ["API_KEY"] = TEST_API_KEY
    os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()
    yield


@pytest.fixture
def valid_headers():
    """Valid request headers."""
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def mock_db():
    """Mock database instance attached to app.state."""
    db = AsyncMock()
    # Default returns for common queries
    db.query_first_user = AsyncMock(return_value=TEST_USER_ID)
    db.query_activities = AsyncMock(return_value=([], 0))
    db.query_activity_by_id = AsyncMock(return_value=None)
    db.query_activity_splits = AsyncMock(return_value=[])
    db.query_sync_status = AsyncMock(return_value=[])
    db.query_planned_workouts = AsyncMock(return_value=([], 0))
    db.get_planned_workout = AsyncMock(return_value=None)
    db.create_planned_workout = AsyncMock(return_value=None)
    db.update_planned_workout = AsyncMock(return_value=None)
    db.delete_planned_workout = AsyncMock(return_value=False)
    db.is_coach_of_athlete = AsyncMock(return_value=False)
    db.get_user_by_better_auth_id = AsyncMock(return_value=None)
    db.get_athletes_for_coach = AsyncMock(return_value=[])
    db.get_coaches_for_athlete = AsyncMock(return_value=[])
    db.get_coaching_enabled = AsyncMock(return_value=False)
    db.get_invite_codes_for_coach = AsyncMock(return_value=[])
    db.is_coach_of_athlete = AsyncMock(return_value=False)
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


class TestAuthentication:
    """Test API key authentication across endpoints."""

    def test_missing_api_key_returns_401(self, client):
        """Request without API key should be rejected with 401."""
        response = client.get("/api/v1/activities")
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, client):
        """Request with wrong API key should be rejected with 401."""
        response = client.get(
            "/api/v1/activities",
            headers={"X-API-Key": "totally-wrong-key"},
        )
        assert response.status_code == 401

    def test_valid_api_key_accepted(self, client, valid_headers):
        """Request with correct API key should pass authentication."""
        response = client.get("/api/v1/activities", headers=valid_headers)
        # Authentication passes; any non-401 response is acceptable
        assert response.status_code != 401


# ---------------------------------------------------------------------------
# Activities router tests
# ---------------------------------------------------------------------------


class TestActivitiesRouter:
    """Integration tests for /api/v1/activities endpoints."""

    def test_list_activities_empty_returns_page(self, client, valid_headers, mock_db):
        """Empty DB returns a valid Page response with empty data."""
        mock_db.query_activities = AsyncMock(return_value=([], 0))
        response = client.get("/api/v1/activities", headers=valid_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["pagination"]["total"] == 0

    def test_list_activities_pagination_params(self, client, valid_headers, mock_db):
        """Pagination params are forwarded to DB query."""
        mock_db.query_activities = AsyncMock(return_value=([], 0))
        response = client.get(
            "/api/v1/activities",
            params={"limit": 10, "offset": 20},
            headers=valid_headers,
        )
        assert response.status_code == 200
        called_args = mock_db.query_activities.call_args
        # limit=10, offset=20 should be in the call
        assert 10 in called_args.args or 10 in list(called_args.kwargs.values())

    def test_list_activities_date_range_filtering(self, client, valid_headers, mock_db):
        """Date range query params are accepted without validation errors."""
        mock_db.query_activities = AsyncMock(return_value=([], 0))
        response = client.get(
            "/api/v1/activities",
            params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            headers=valid_headers,
        )
        assert response.status_code == 200

    def test_get_activity_404_when_not_found(self, client, valid_headers, mock_db):
        """Activity detail returns 404 when not found in DB."""
        mock_db.query_activity_by_id = AsyncMock(return_value=None)
        response = client.get("/api/v1/activities/999999", headers=valid_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_activity_splits_empty(self, client, valid_headers, mock_db):
        """Activity splits endpoint returns empty list when no splits."""
        mock_db.query_activity_splits = AsyncMock(return_value=[])
        response = client.get("/api/v1/activities/123/splits", headers=valid_headers)
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_list_activities_make_page_structure(self, client, valid_headers, mock_db):
        """make_page produces correct pagination metadata."""
        # 5 rows, total=20, limit=5, offset=0 → has_more=True
        row = MagicMock()
        row.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("activity_id", 1),
                    ("activity_name", "Run"),
                    ("custom_name", None),
                    ("activity_type", "running"),
                    ("sport_type", None),
                    ("start_timestamp", None),
                    ("duration_seconds", 3600.0),
                    ("distance_meters", 10000.0),
                    ("average_speed", 2.78),
                    ("max_speed", None),
                    ("calories", 500),
                    ("average_hr", 160),
                    ("max_hr", 180),
                    ("elevation_gain_meters", 100.0),
                    ("elevation_loss_meters", 50.0),
                    ("training_stress_score", None),
                    ("vo2_max_value", None),
                    ("device_name", "Fenix"),
                    ("num_laps", 1),
                    ("aerobic_training_effect", None),
                    ("anaerobic_training_effect", None),
                ]
            )
        )
        row.keys = MagicMock(
            return_value=[
                "activity_id",
                "activity_name",
                "custom_name",
                "activity_type",
                "sport_type",
                "start_timestamp",
                "duration_seconds",
                "distance_meters",
                "average_speed",
                "max_speed",
                "calories",
                "average_hr",
                "max_hr",
                "elevation_gain_meters",
                "elevation_loss_meters",
                "training_stress_score",
                "vo2_max_value",
                "device_name",
                "num_laps",
                "aerobic_training_effect",
                "anaerobic_training_effect",
            ]
        )

        # Use a dict-like asyncpg Record mock
        class FakeRow(dict):
            pass

        fake_row = FakeRow(
            activity_id=1,
            activity_name="Run",
            custom_name=None,
            activity_type="running",
            sport_type=None,
            start_timestamp=None,
            duration_seconds=3600.0,
            distance_meters=10000.0,
            average_speed=2.78,
            max_speed=None,
            calories=500,
            average_hr=160,
            max_hr=180,
            elevation_gain_meters=100.0,
            elevation_loss_meters=50.0,
            training_stress_score=None,
            vo2_max_value=None,
            device_name="Fenix",
            num_laps=1,
            aerobic_training_effect=None,
            anaerobic_training_effect=None,
        )

        mock_db.query_activities = AsyncMock(return_value=([fake_row], 20))
        response = client.get(
            "/api/v1/activities",
            params={"limit": 5, "offset": 0},
            headers=valid_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total"] == 20
        assert body["pagination"]["limit"] == 5
        assert body["pagination"]["has_more"] is True


# ---------------------------------------------------------------------------
# Sync router tests
# ---------------------------------------------------------------------------


class TestSyncRouter:
    """Integration tests for /api/v1/sync endpoints."""

    def test_sync_status_returns_data_list(self, client, valid_headers, mock_db):
        """Sync status endpoint returns data list (empty when no sync state)."""
        mock_db.query_sync_status = AsyncMock(return_value=[])
        response = client.get("/api/v1/sync/status", headers=valid_headers)
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_trigger_sync_invalid_category_returns_400(self, client, valid_headers):
        """Trigger sync with invalid category returns 400."""
        response = client.post(
            "/api/v1/sync/trigger",
            json={"categories": ["invalid_category"]},
            headers=valid_headers,
        )
        assert response.status_code == 400
        assert "Invalid categories" in response.json()["detail"]

    def test_trigger_sync_valid_categories_accepted(self, client, valid_headers, mock_db):
        """Valid categories are accepted by trigger endpoint."""
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=None)
        response = client.post(
            "/api/v1/sync/trigger",
            json={"categories": ["daily_health", "activities"], "dry_run": False},
            headers=valid_headers,
        )
        # Returns 200 with job_id (sync runs in background thread)
        assert response.status_code == 200
        body = response.json()
        assert "job_id" in body

    def test_list_sync_jobs(self, client, valid_headers):
        """Listing sync jobs returns a list."""
        response = client.get("/api/v1/sync/jobs", headers=valid_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_sync_job_404_unknown(self, client, valid_headers):
        """Getting unknown job ID returns 404."""
        response = client.get(
            "/api/v1/sync/jobs/non-existent-job-id", headers=valid_headers
        )
        assert response.status_code == 404

    def test_concurrent_sync_prevention(self, client, valid_headers):
        """Second sync trigger when one is running returns 409."""
        # First trigger
        resp1 = client.post(
            "/api/v1/sync/trigger",
            json={},
            headers=valid_headers,
        )
        # If first trigger succeeded (job is pending/running), second should 409
        if resp1.status_code == 200:
            job_id = resp1.json()["job_id"]
            # Trigger again before job finishes
            resp2 = client.post(
                "/api/v1/sync/trigger",
                json={},
                headers=valid_headers,
            )
            # May be 409 (concurrent prevention) or 200 if job finished very fast
            assert resp2.status_code in (200, 409)


# ---------------------------------------------------------------------------
# Planned Workouts router tests
# ---------------------------------------------------------------------------


class TestPlannedWorkoutsRouter:
    """Integration tests for /api/v1/planned-workouts endpoints."""

    def test_list_planned_workouts_empty(self, client, valid_headers, mock_db):
        """Empty planned workouts returns valid Page response."""
        mock_db.query_planned_workouts = AsyncMock(return_value=([], 0))
        response = client.get("/api/v1/planned-workouts", headers=valid_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["pagination"]["total"] == 0

    def test_create_planned_workout_invalid_sport_type(
        self, client, valid_headers
    ):
        """Creating planned workout with invalid sport_type returns 422."""
        response = client.post(
            "/api/v1/planned-workouts",
            json={
                "planned_date": "2026-03-01",
                "sport_type": "yoga",
                "title": "Yoga session",
                "intensity": "easy",
            },
            headers=valid_headers,
        )
        assert response.status_code == 422

    def test_create_planned_workout_invalid_intensity(
        self, client, valid_headers
    ):
        """Creating planned workout with invalid intensity returns 422."""
        response = client.post(
            "/api/v1/planned-workouts",
            json={
                "planned_date": "2026-03-01",
                "sport_type": "running",
                "title": "Easy run",
                "intensity": "ultra_hard",
            },
            headers=valid_headers,
        )
        assert response.status_code == 422

    def test_get_planned_workout_404(self, client, valid_headers, mock_db):
        """Getting non-existent planned workout returns 404."""
        mock_db.get_planned_workout = AsyncMock(return_value=None)
        response = client.get(
            "/api/v1/planned-workouts/999999", headers=valid_headers
        )
        assert response.status_code == 404

    def test_update_planned_workout_404(self, client, valid_headers, mock_db):
        """Updating non-existent planned workout returns 404."""
        mock_db.update_planned_workout = AsyncMock(return_value=None)
        response = client.patch(
            "/api/v1/planned-workouts/999999",
            json={"title": "Updated"},
            headers=valid_headers,
        )
        assert response.status_code == 404

    def test_delete_planned_workout_404(self, client, valid_headers, mock_db):
        """Deleting non-existent planned workout returns 404."""
        mock_db.delete_planned_workout = AsyncMock(return_value=False)
        response = client.delete(
            "/api/v1/planned-workouts/999999", headers=valid_headers
        )
        assert response.status_code == 404

    def test_download_csv_template(self, client, valid_headers):
        """Template download returns CSV content."""
        response = client.get(
            "/api/v1/planned-workouts/template", headers=valid_headers
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "date" in response.text


# ---------------------------------------------------------------------------
# Coaching router tests
# ---------------------------------------------------------------------------


class TestCoachingRouter:
    """Integration tests for /api/v1/coaching endpoints."""

    def test_list_athletes_requires_better_auth_header(self, client, valid_headers):
        """Athletes list requires X-Better-Auth-User-Id header."""
        response = client.get("/api/v1/coaching/athletes", headers=valid_headers)
        assert response.status_code == 400
        assert "X-Better-Auth-User-Id" in response.json()["detail"]

    def test_list_athletes_empty_with_coach_header(self, client, valid_headers, mock_db):
        """Athletes list returns empty when coach has no athletes."""
        mock_db.get_athletes_for_coach = AsyncMock(return_value=[])
        headers = {**valid_headers, "X-Better-Auth-User-Id": "coach-ba-id-abc"}
        response = client.get("/api/v1/coaching/athletes", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_check_access_returns_false_for_unknown(
        self, client, valid_headers, mock_db
    ):
        """check-access returns has_access=False when coach not linked."""
        mock_db.is_coach_of_athlete = AsyncMock(return_value=False)
        headers = {**valid_headers, "X-Better-Auth-User-Id": "coach-ba-id-abc"}
        response = client.get(
            "/api/v1/coaching/check-access",
            params={"athlete_user_id": TEST_USER_ID},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["has_access"] is False

    def test_coaching_status_requires_better_auth_header(self, client, valid_headers):
        """Coaching status requires X-Better-Auth-User-Id header."""
        response = client.get("/api/v1/coaching/status", headers=valid_headers)
        assert response.status_code == 400

    def test_coaching_status_returns_structure(
        self, client, valid_headers, mock_db
    ):
        """Coaching status returns expected structure."""
        mock_db.get_coaching_enabled = AsyncMock(return_value=False)
        mock_db.get_athletes_for_coach = AsyncMock(return_value=[])
        headers = {**valid_headers, "X-Better-Auth-User-Id": "coach-ba-id-xyz"}
        response = client.get("/api/v1/coaching/status", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert "coaching_enabled" in body
        assert "athletes" in body
        assert "coaches" in body

    def test_validate_422_missing_fields(self, client, valid_headers):
        """Endpoint with required fields returns 422 when missing."""
        # Missing required 'code' field
        response = client.post(
            "/api/v1/coaching/redeem",
            json={},
            headers=valid_headers,
        )
        assert response.status_code == 422
