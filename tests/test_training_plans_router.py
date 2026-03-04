"""Tests for the training_plans router (/api/v1/training-plans/)."""

import os
import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.token_manager import TokenManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_API_KEY = "training-plans-test-api-key-5678"
TEST_USER_ID = 1


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------


def _make_plan_row(plan_id: int = 1) -> dict:
    """Return a minimal dict that validates as TrainingPlanSummary/Detail."""
    return {
        "id": plan_id,
        "user_id": TEST_USER_ID,
        "race_target_id": 10,
        "name": "UTMB 12-Week Plan",
        "status": "active",
        "start_date": date(2026, 4, 1),
        "end_date": date(2026, 6, 24),
        "total_weeks": 12,
        "experience_level": "intermediate",
        "created_by_user_id": None,
        "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        "generation_params": {"race_km": 170},
        "weeks": [],
    }


def _make_week_row(week_id: int = 1, plan_id: int = 1, week_number: int = 1) -> dict:
    """Return a minimal dict that validates as PlanWeekSummary/Detail."""
    return {
        "id": week_id,
        "plan_id": plan_id,
        "week_number": week_number,
        "phase": "base",
        "is_recovery_week": False,
        "target_tss": 300.0,
        "target_volume_km": 60.0,
        "target_elevation_m": 1500,
        "target_sessions": 4,
        "notes": None,
        "sessions": [],
    }


def _make_session_row(session_id: int = 1, plan_id: int = 1, week_id: int = 1) -> dict:
    """Return a minimal dict that validates as PlanSessionResponse."""
    return {
        "id": session_id,
        "plan_id": plan_id,
        "week_id": week_id,
        "planned_workout_id": None,
        "day_of_week": 1,
        "session_type": "EF",
        "title": "Easy run",
        "description": "Zone 2 aerobic run",
        "sport_type": "trail_running",
        "target_duration_seconds": 3600,
        "target_distance_meters": 10000.0,
        "target_elevation_gain_m": 200,
        "target_tss": 50.0,
        "hr_zone_primary": 2,
        "intensity": "easy",
        "blocks": None,
        "sort_order": 0,
        "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }


def _make_profile_row(user_id: int = TEST_USER_ID) -> dict:
    """Return a minimal dict that validates as AthleteProfileResponse."""
    return {
        "id": 1,
        "user_id": user_id,
        "birth_date": date(1985, 6, 15),
        "gender": "M",
        "height_cm": 178.0,
        "experience_level": "intermediate",
        "available_days_per_week": 4,
        "available_slots": None,
        "injury_history": None,
        "has_hill_access": True,
        "has_gym_access": False,
        "fc_max": 185,
        "fc_repos": 48,
        "fthr": 162,
        "day_preferences": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


def _make_race_row(race_id: int = 10, user_id: int = TEST_USER_ID) -> dict:
    """Return a minimal dict that validates as RaceTargetResponse."""
    return {
        "id": race_id,
        "user_id": user_id,
        "race_name": "UTMB",
        "race_date": date(2026, 8, 29),
        "distance_km": 171.0,
        "elevation_gain_m": 10000,
        "elevation_loss_m": 10000,
        "altitude_min_m": 800,
        "altitude_max_m": 4807,
        "technical_percent": 40,
        "cutoff_hours": 46.5,
        "itra_points": 6,
        "objective": "finish",
        "elevation_profile": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


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
def invalid_headers():
    """Invalid API request headers."""
    return {"X-API-Key": "wrong-key"}


@pytest.fixture
def mock_db():
    """Mock database with all methods needed by training_plans router."""
    db = AsyncMock()
    db.query_first_user = AsyncMock(return_value=TEST_USER_ID)
    # pool is used by db_ops functions that call pool.fetchrow/fetch/execute directly
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=None)
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchval = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value=None)
    db.pool = pool
    return db


@pytest.fixture
def client(mock_db):
    """TestClient with mocked DB injected into app.state."""
    app.state.db = mock_db
    app.state.user_id = TEST_USER_ID
    app.state.start_time = datetime.now(timezone.utc)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Auth guard: all endpoints must require X-API-Key
# ---------------------------------------------------------------------------


class TestTrainingPlansAuthRequired:
    """All training-plans endpoints must reject requests without a valid API key."""

    def test_generate_without_api_key_returns_401(self, client):
        response = client.post("/api/v1/training-plans/generate", json={
            "race_target_id": 1,
        })
        assert response.status_code == 401

    def test_list_plans_without_api_key_returns_401(self, client):
        response = client.get("/api/v1/training-plans")
        assert response.status_code == 401

    def test_get_plan_without_api_key_returns_401(self, client):
        response = client.get("/api/v1/training-plans/1")
        assert response.status_code == 401

    def test_patch_plan_without_api_key_returns_401(self, client):
        response = client.patch("/api/v1/training-plans/1", json={"status": "active"})
        assert response.status_code == 401

    def test_delete_plan_without_api_key_returns_401(self, client):
        response = client.delete("/api/v1/training-plans/1")
        assert response.status_code == 401

    def test_get_week_without_api_key_returns_401(self, client):
        response = client.get("/api/v1/training-plans/1/weeks/1")
        assert response.status_code == 401

    def test_get_profile_without_api_key_returns_401(self, client):
        response = client.get("/api/v1/training-plans/profile")
        assert response.status_code == 401

    def test_get_races_without_api_key_returns_401(self, client):
        response = client.get("/api/v1/training-plans/races")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/training-plans (list)
# ---------------------------------------------------------------------------


class TestListTrainingPlans:
    """Tests for GET /api/v1/training-plans."""

    def test_list_returns_empty_page_when_no_plans(self, client, valid_headers, mock_db):
        """GET /training-plans returns a paginated empty response when there are no plans."""
        with patch("src.api.routers.training_plans.db_ops.list_training_plans",
                   new=AsyncMock(return_value=([], 0))):
            response = client.get("/api/v1/training-plans", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["pagination"]["total"] == 0

    def test_list_returns_plans(self, client, valid_headers):
        """GET /training-plans returns plans in paginated data array."""
        plan = _make_plan_row(plan_id=1)

        with patch("src.api.routers.training_plans.db_ops.list_training_plans",
                   new=AsyncMock(return_value=([plan], 1))):
            response = client.get("/api/v1/training-plans", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] == 1
        assert body["data"][0]["name"] == "UTMB 12-Week Plan"
        assert body["pagination"]["total"] == 1

    def test_list_with_invalid_api_key_returns_401(self, client, invalid_headers):
        """GET /training-plans with wrong API key returns 401."""
        response = client.get("/api/v1/training-plans", headers=invalid_headers)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/training-plans/{plan_id}
# ---------------------------------------------------------------------------


class TestGetTrainingPlan:
    """Tests for GET /api/v1/training-plans/{plan_id}."""

    def test_get_plan_returns_plan_with_weeks(self, client, valid_headers):
        """GET /training-plans/1 returns the plan and its weeks."""
        plan = _make_plan_row(plan_id=1)
        weeks = [_make_week_row(week_id=1, plan_id=1, week_number=1)]

        with (
            patch("src.api.routers.training_plans.db_ops.get_training_plan",
                  new=AsyncMock(return_value=plan)),
            patch("src.api.routers.training_plans.db_ops.get_plan_weeks",
                  new=AsyncMock(return_value=weeks)),
        ):
            response = client.get("/api/v1/training-plans/1", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == 1
        assert body["name"] == "UTMB 12-Week Plan"
        assert len(body["weeks"]) == 1
        assert body["weeks"][0]["week_number"] == 1

    def test_get_plan_not_found_returns_404(self, client, valid_headers):
        """GET /training-plans/999 returns 404 when plan does not exist."""
        with patch("src.api.routers.training_plans.db_ops.get_training_plan",
                   new=AsyncMock(return_value=None)):
            response = client.get("/api/v1/training-plans/999", headers=valid_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_plan_decodes_string_generation_params(self, client, valid_headers):
        """GET /training-plans/1 auto-decodes double-encoded generation_params JSON string."""
        import json
        plan = _make_plan_row(plan_id=1)
        plan["generation_params"] = json.dumps({"race_km": 170, "weeks": 12})  # double-encoded string

        with (
            patch("src.api.routers.training_plans.db_ops.get_training_plan",
                  new=AsyncMock(return_value=plan)),
            patch("src.api.routers.training_plans.db_ops.get_plan_weeks",
                  new=AsyncMock(return_value=[])),
        ):
            response = client.get("/api/v1/training-plans/1", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        # After decoding, generation_params must be a dict, not a string
        assert isinstance(body["generation_params"], dict)
        assert body["generation_params"]["race_km"] == 170


# ---------------------------------------------------------------------------
# PATCH /api/v1/training-plans/{plan_id}
# ---------------------------------------------------------------------------


class TestUpdateTrainingPlanStatus:
    """Tests for PATCH /api/v1/training-plans/{plan_id}."""

    def test_patch_plan_status_to_active(self, client, valid_headers):
        """PATCH /training-plans/1 with status=active updates the plan."""
        updated = {**_make_plan_row(plan_id=1), "status": "active"}

        with patch("src.api.routers.training_plans.db_ops.update_training_plan_status",
                   new=AsyncMock(return_value=updated)):
            response = client.patch(
                "/api/v1/training-plans/1",
                json={"status": "active"},
                headers=valid_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "active"

    def test_patch_plan_status_to_cancelled(self, client, valid_headers):
        """PATCH /training-plans/1 with status=cancelled updates the plan."""
        updated = {**_make_plan_row(plan_id=1), "status": "cancelled"}

        with patch("src.api.routers.training_plans.db_ops.update_training_plan_status",
                   new=AsyncMock(return_value=updated)):
            response = client.patch(
                "/api/v1/training-plans/1",
                json={"status": "cancelled"},
                headers=valid_headers,
            )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_patch_plan_invalid_status_returns_422(self, client, valid_headers):
        """PATCH /training-plans/1 with invalid status returns 422."""
        response = client.patch(
            "/api/v1/training-plans/1",
            json={"status": "invalid_status"},
            headers=valid_headers,
        )
        assert response.status_code == 422

    def test_patch_plan_not_found_returns_404(self, client, valid_headers):
        """PATCH /training-plans/999 returns 404 when plan does not exist."""
        with patch("src.api.routers.training_plans.db_ops.update_training_plan_status",
                   new=AsyncMock(return_value=None)):
            response = client.patch(
                "/api/v1/training-plans/999",
                json={"status": "completed"},
                headers=valid_headers,
            )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/training-plans/{plan_id}
# ---------------------------------------------------------------------------


class TestDeleteTrainingPlan:
    """Tests for DELETE /api/v1/training-plans/{plan_id}."""

    def test_delete_plan_returns_204(self, client, valid_headers):
        """DELETE /training-plans/1 returns 204 No Content on success."""
        with patch("src.api.routers.training_plans.db_ops.delete_training_plan",
                   new=AsyncMock(return_value=True)):
            response = client.delete("/api/v1/training-plans/1", headers=valid_headers)

        assert response.status_code == 204

    def test_delete_plan_not_found_returns_404(self, client, valid_headers):
        """DELETE /training-plans/999 returns 404 when plan does not exist."""
        with patch("src.api.routers.training_plans.db_ops.delete_training_plan",
                   new=AsyncMock(return_value=False)):
            response = client.delete("/api/v1/training-plans/999", headers=valid_headers)

        assert response.status_code == 404

    def test_delete_without_api_key_returns_401(self, client):
        """DELETE /training-plans/1 without API key returns 401."""
        response = client.delete("/api/v1/training-plans/1")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/training-plans/{plan_id}/weeks/{week_number}
# ---------------------------------------------------------------------------


class TestGetPlanWeek:
    """Tests for GET /api/v1/training-plans/{plan_id}/weeks/{week_number}."""

    def test_get_week_returns_week_with_sessions(self, client, valid_headers):
        """GET /training-plans/1/weeks/1 returns the week with sessions."""
        plan = _make_plan_row(plan_id=1)
        week = _make_week_row(week_id=1, plan_id=1, week_number=1)
        sessions = [_make_session_row(session_id=1, plan_id=1, week_id=1)]

        with (
            patch("src.api.routers.training_plans.db_ops.get_training_plan",
                  new=AsyncMock(return_value=plan)),
            patch("src.api.routers.training_plans.db_ops.get_plan_week_by_number",
                  new=AsyncMock(return_value=week)),
            patch("src.api.routers.training_plans.db_ops.get_plan_sessions_for_week",
                  new=AsyncMock(return_value=sessions)),
        ):
            response = client.get("/api/v1/training-plans/1/weeks/1", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["week_number"] == 1
        assert body["phase"] == "base"
        assert len(body["sessions"]) == 1
        assert body["sessions"][0]["session_type"] == "EF"

    def test_get_week_plan_not_found_returns_404(self, client, valid_headers):
        """GET /training-plans/999/weeks/1 returns 404 when plan does not exist."""
        with patch("src.api.routers.training_plans.db_ops.get_training_plan",
                   new=AsyncMock(return_value=None)):
            response = client.get("/api/v1/training-plans/999/weeks/1", headers=valid_headers)

        assert response.status_code == 404
        assert "Training plan not found" in response.json()["detail"]

    def test_get_week_not_found_returns_404(self, client, valid_headers):
        """GET /training-plans/1/weeks/99 returns 404 when week does not exist."""
        plan = _make_plan_row(plan_id=1)

        with (
            patch("src.api.routers.training_plans.db_ops.get_training_plan",
                  new=AsyncMock(return_value=plan)),
            patch("src.api.routers.training_plans.db_ops.get_plan_week_by_number",
                  new=AsyncMock(return_value=None)),
        ):
            response = client.get("/api/v1/training-plans/1/weeks/99", headers=valid_headers)

        assert response.status_code == 404
        assert "Week not found" in response.json()["detail"]

    def test_get_week_decodes_string_session_blocks(self, client, valid_headers):
        """GET /training-plans/1/weeks/1 auto-decodes double-encoded session blocks."""
        import json
        plan = _make_plan_row(plan_id=1)
        week = _make_week_row(week_id=1, plan_id=1, week_number=1)
        session = _make_session_row()
        session["blocks"] = json.dumps([{"type": "warmup", "duration_s": 600}])  # string instead of list

        with (
            patch("src.api.routers.training_plans.db_ops.get_training_plan",
                  new=AsyncMock(return_value=plan)),
            patch("src.api.routers.training_plans.db_ops.get_plan_week_by_number",
                  new=AsyncMock(return_value=week)),
            patch("src.api.routers.training_plans.db_ops.get_plan_sessions_for_week",
                  new=AsyncMock(return_value=[session])),
        ):
            response = client.get("/api/v1/training-plans/1/weeks/1", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        session_blocks = body["sessions"][0]["blocks"]
        assert isinstance(session_blocks, list)
        assert session_blocks[0]["type"] == "warmup"


# ---------------------------------------------------------------------------
# POST /api/v1/training-plans/generate
# ---------------------------------------------------------------------------


class TestGenerateTrainingPlan:
    """Tests for POST /api/v1/training-plans/generate."""

    def test_generate_plan_returns_201_on_success(self, client, valid_headers):
        """POST /generate returns 201 Created on success."""
        plan = _make_plan_row(plan_id=5)

        with patch("src.api.routers.training_plans.generate_plan",
                   new=AsyncMock(return_value=plan)):
            response = client.post(
                "/api/v1/training-plans/generate",
                json={
                    "race_target_id": 10,
                    "plan_name": "UTMB Prep",
                    "total_weeks": 12,
                    "start_date": "2026-04-01",
                },
                headers=valid_headers,
            )

        assert response.status_code == 201

    def test_generate_plan_value_error_returns_422(self, client, valid_headers):
        """POST /generate returns 422 when generate_plan raises ValueError."""
        with patch("src.api.routers.training_plans.generate_plan",
                   new=AsyncMock(side_effect=ValueError("Invalid race target"))):
            response = client.post(
                "/api/v1/training-plans/generate",
                json={"race_target_id": 99},
                headers=valid_headers,
            )

        assert response.status_code == 422
        assert "Invalid race target" in response.json()["detail"]

    def test_generate_plan_unexpected_error_returns_500(self, client, valid_headers):
        """POST /generate returns 500 on unexpected errors."""
        with patch("src.api.routers.training_plans.generate_plan",
                   new=AsyncMock(side_effect=RuntimeError("DB connection lost"))):
            response = client.post(
                "/api/v1/training-plans/generate",
                json={"race_target_id": 10},
                headers=valid_headers,
            )

        assert response.status_code == 500
        assert "Plan generation error" in response.json()["detail"]

    def test_generate_plan_missing_race_target_id_returns_422(self, client, valid_headers):
        """POST /generate without race_target_id returns 422 validation error."""
        response = client.post(
            "/api/v1/training-plans/generate",
            json={"plan_name": "My plan"},  # missing required race_target_id
            headers=valid_headers,
        )
        assert response.status_code == 422

    def test_generate_plan_without_api_key_returns_401(self, client):
        """POST /generate without API key returns 401."""
        response = client.post(
            "/api/v1/training-plans/generate",
            json={"race_target_id": 10},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/training-plans/profile
# ---------------------------------------------------------------------------


class TestAthleteProfile:
    """Tests for GET /PUT /api/v1/training-plans/profile."""

    def test_get_profile_returns_profile(self, client, valid_headers):
        """GET /training-plans/profile returns the athlete's profile."""
        profile = _make_profile_row()

        with patch("src.api.routers.training_plans.db_ops.get_athlete_profile",
                   new=AsyncMock(return_value=profile)):
            response = client.get("/api/v1/training-plans/profile", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == TEST_USER_ID
        assert body["experience_level"] == "intermediate"
        assert body["has_hill_access"] is True

    def test_get_profile_not_found_returns_404(self, client, valid_headers):
        """GET /training-plans/profile returns 404 when profile does not exist."""
        with patch("src.api.routers.training_plans.db_ops.get_athlete_profile",
                   new=AsyncMock(return_value=None)):
            response = client.get("/api/v1/training-plans/profile", headers=valid_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_put_profile_creates_or_updates(self, client, valid_headers):
        """PUT /training-plans/profile creates or updates athlete profile."""
        profile = _make_profile_row()

        with patch("src.api.routers.training_plans.db_ops.upsert_athlete_profile",
                   new=AsyncMock(return_value=profile)):
            response = client.put(
                "/api/v1/training-plans/profile",
                json={
                    "experience_level": "intermediate",
                    "available_days_per_week": 4,
                    "has_hill_access": True,
                    "has_gym_access": False,
                },
                headers=valid_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["experience_level"] == "intermediate"

    def test_get_profile_without_api_key_returns_401(self, client):
        """GET /training-plans/profile without API key returns 401."""
        response = client.get("/api/v1/training-plans/profile")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET/POST/DELETE /api/v1/training-plans/races
# ---------------------------------------------------------------------------


class TestRaceTargets:
    """Tests for race target endpoints."""

    def test_list_races_returns_empty_list(self, client, valid_headers):
        """GET /training-plans/races returns empty list when no races."""
        with patch("src.api.routers.training_plans.db_ops.list_race_targets",
                   new=AsyncMock(return_value=[])):
            response = client.get("/api/v1/training-plans/races", headers=valid_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_races_returns_races(self, client, valid_headers):
        """GET /training-plans/races returns list of race targets."""
        race = _make_race_row()

        with patch("src.api.routers.training_plans.db_ops.list_race_targets",
                   new=AsyncMock(return_value=[race])):
            response = client.get("/api/v1/training-plans/races", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["race_name"] == "UTMB"

    def test_create_race_returns_201(self, client, valid_headers):
        """POST /training-plans/races returns 201 with the created race."""
        race = _make_race_row(race_id=10)

        with patch("src.api.routers.training_plans.db_ops.create_race_target",
                   new=AsyncMock(return_value=race)):
            response = client.post(
                "/api/v1/training-plans/races",
                json={
                    "race_name": "UTMB",
                    "race_date": "2026-08-29",
                    "distance_km": 171.0,
                    "elevation_gain_m": 10000,
                },
                headers=valid_headers,
            )

        assert response.status_code == 201
        body = response.json()
        assert body["race_name"] == "UTMB"
        assert body["id"] == 10

    def test_delete_race_returns_204(self, client, valid_headers):
        """DELETE /training-plans/races/10 returns 204 on success."""
        with patch("src.api.routers.training_plans.db_ops.delete_race_target",
                   new=AsyncMock(return_value=True)):
            response = client.delete("/api/v1/training-plans/races/10", headers=valid_headers)

        assert response.status_code == 204

    def test_delete_race_not_found_returns_404(self, client, valid_headers):
        """DELETE /training-plans/races/999 returns 404 when race does not exist."""
        with patch("src.api.routers.training_plans.db_ops.delete_race_target",
                   new=AsyncMock(return_value=False)):
            response = client.delete("/api/v1/training-plans/races/999", headers=valid_headers)

        assert response.status_code == 404

    def test_create_race_missing_required_field_returns_422(self, client, valid_headers):
        """POST /training-plans/races without required race_date returns 422."""
        response = client.post(
            "/api/v1/training-plans/races",
            json={"race_name": "UTMB", "distance_km": 171.0},  # missing race_date
            headers=valid_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/training-plans/fitness-snapshot
# ---------------------------------------------------------------------------


class TestFitnessSnapshot:
    """Tests for GET /api/v1/training-plans/fitness-snapshot."""

    def test_get_fitness_snapshot_returns_snapshot(self, client, valid_headers):
        """GET /fitness-snapshot returns current fitness data."""
        from src.training.fitness_snapshot import UserFitnessData

        snapshot = UserFitnessData(
            vo2_max=52.5,
            resting_hr=48,
            max_hr=185,
            weight_kg=72.0,
            vma_kmh=17.5,
            weekly_volume_km=60.0,
            weekly_elevation_m=1500,
        )

        with patch("src.api.routers.training_plans.build_fitness_snapshot",
                   new=AsyncMock(return_value=snapshot)):
            response = client.get("/api/v1/training-plans/fitness-snapshot", headers=valid_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["vo2_max"] == 52.5
        assert body["resting_hr"] == 48
        assert body["vma_kmh"] == 17.5

    def test_get_fitness_snapshot_without_api_key_returns_401(self, client):
        """GET /fitness-snapshot without API key returns 401."""
        response = client.get("/api/v1/training-plans/fitness-snapshot")
        assert response.status_code == 401
