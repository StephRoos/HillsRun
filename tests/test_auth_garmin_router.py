"""Tests for the auth_garmin router (/api/v1/auth/)."""

import os
import time
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.token_manager import TokenManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_API_KEY = "auth-garmin-test-api-key-1234"
TEST_USER_ID = 42
TEST_BETTER_AUTH_USER_ID = "better-auth-user-abc123"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_env():
    """Set required environment variables before each test and disable rate limiter."""
    os.environ["API_KEY"] = TEST_API_KEY
    os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()
    # Disable slowapi rate limiter so the /connect and /connect/mfa decorators
    # don't crash in tests (they require the 'request' kwarg name from slowapi)
    from src.api.rate_limit import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True
    # Clean up MFA sessions between tests to avoid cross-test contamination
    from src.api.routers.auth_garmin import _mfa_sessions
    _mfa_sessions.clear()


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
    """Mock database with default method stubs for auth_garmin tests."""
    db = AsyncMock()
    db.get_user_by_better_auth_id = AsyncMock(return_value=None)
    db.get_user_by_email = AsyncMock(return_value=None)
    db.get_or_create_user_with_link = AsyncMock(return_value=TEST_USER_ID)
    db.store_encrypted_tokens = AsyncMock(return_value=None)
    db.get_user_info = AsyncMock(return_value=None)
    db.query_sync_status = AsyncMock(return_value=[])
    db.unlink_better_auth_user = AsyncMock(return_value=None)
    db.query_first_user = AsyncMock(return_value=TEST_USER_ID)
    # pool.acquire() used in _finalize_connect for existing users
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    db.pool = MagicMock()
    db.pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))
    return db


@pytest.fixture
def client(mock_db):
    """TestClient with mocked DB injected into app.state."""
    app.state.db = mock_db
    app.state.user_id = TEST_USER_ID
    app.state.start_time = datetime.now(timezone.utc)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helper: build a mock Garmin client post-login
# ---------------------------------------------------------------------------


def _make_mock_garmin(display_name="TrailRunner42"):
    """Return a mock Garmin client that looks authenticated."""
    garmin_client = MagicMock()
    garmin_client.display_name = display_name
    garmin_client.full_name = display_name
    garmin_client.login = MagicMock(return_value=None)  # non-tuple → no MFA
    garmin_client.garth = MagicMock()
    garmin_client.garth.dumps = MagicMock(return_value="fake-token-data")
    garmin_client.garth.oauth1_token = None
    garmin_client.garth.oauth2_token = None
    garmin_client.garth.connectapi = MagicMock(return_value={
        "displayName": display_name,
        "fullName": display_name,
    })
    return garmin_client


# ---------------------------------------------------------------------------
# POST /connect — success (no MFA)
# ---------------------------------------------------------------------------


class TestConnectSuccess:
    """Tests for POST /api/v1/auth/connect success path."""

    def test_connect_success_no_mfa(self, client, valid_headers, mock_db):
        """POST /connect returns connected=True when Garmin login succeeds without MFA."""
        mock_garmin = _make_mock_garmin("TrailRunner42")

        with patch("src.api.routers.auth_garmin.Garmin", return_value=mock_garmin):
            response = client.post(
                "/api/v1/auth/connect",
                json={
                    "email": "trail@runner.com",
                    "password": "secret",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is True
        assert body["needs_mfa"] is False
        assert body["mfa_session_id"] is None
        assert body["garmin_display_name"] == "TrailRunner42"
        assert body["user_id"] == TEST_USER_ID

    def test_connect_success_calls_store_encrypted_tokens(self, client, valid_headers, mock_db):
        """POST /connect stores encrypted tokens after successful login."""
        mock_garmin = _make_mock_garmin()

        with patch("src.api.routers.auth_garmin.Garmin", return_value=mock_garmin):
            client.post(
                "/api/v1/auth/connect",
                json={
                    "email": "trail@runner.com",
                    "password": "secret",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        mock_db.store_encrypted_tokens.assert_called_once()
        call_args = mock_db.store_encrypted_tokens.call_args
        assert call_args[0][0] == TEST_USER_ID
        # Second arg is the encrypted blob (bytes or str) — just check it's non-empty
        encrypted = call_args[0][1]
        assert encrypted is not None
        assert len(encrypted) > 0

    def test_connect_existing_user_reconnect(self, client, valid_headers, mock_db):
        """POST /connect reuses existing garmin_user when better_auth_user_id matches."""
        existing_user_id = 99
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=existing_user_id)

        mock_garmin = _make_mock_garmin("ExistingRunner")

        with patch("src.api.routers.auth_garmin.Garmin", return_value=mock_garmin):
            response = client.post(
                "/api/v1/auth/connect",
                json={
                    "email": "existing@runner.com",
                    "password": "secret",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is True
        assert body["user_id"] == existing_user_id
        # Should NOT create a new user — pool.acquire used for UPDATE instead
        mock_db.get_or_create_user_with_link.assert_not_called()


# ---------------------------------------------------------------------------
# POST /connect — MFA required
# ---------------------------------------------------------------------------


class TestConnectMfa:
    """Tests for POST /api/v1/auth/connect when MFA is needed."""

    def test_connect_returns_mfa_session_when_login_needs_mfa(self, client, valid_headers, mock_db):
        """POST /connect returns needs_mfa=True and a session_id when Garmin requires MFA."""
        mock_garmin = _make_mock_garmin()
        fake_client_state = {"mfa_state": "pending"}
        mock_garmin.login = MagicMock(return_value=("needs_mfa", fake_client_state))

        with patch("src.api.routers.auth_garmin.Garmin", return_value=mock_garmin):
            response = client.post(
                "/api/v1/auth/connect",
                json={
                    "email": "mfa@runner.com",
                    "password": "secret",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is False
        assert body["needs_mfa"] is True
        assert body["mfa_session_id"] is not None
        assert len(body["mfa_session_id"]) > 0

    def test_connect_mfa_session_stored_in_memory(self, client, valid_headers, mock_db):
        """POST /connect stores MFA session in the in-memory store."""
        from src.api.routers.auth_garmin import _mfa_sessions

        mock_garmin = _make_mock_garmin()
        mock_garmin.login = MagicMock(return_value=("needs_mfa", {"state": "x"}))

        with patch("src.api.routers.auth_garmin.Garmin", return_value=mock_garmin):
            response = client.post(
                "/api/v1/auth/connect",
                json={
                    "email": "mfa@runner.com",
                    "password": "pass",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        session_id = response.json()["mfa_session_id"]
        assert session_id in _mfa_sessions
        session = _mfa_sessions[session_id]
        assert session["email"] == "mfa@runner.com"
        assert session["better_auth_user_id"] == TEST_BETTER_AUTH_USER_ID


# ---------------------------------------------------------------------------
# POST /connect — error cases
# ---------------------------------------------------------------------------


class TestConnectErrors:
    """Tests for POST /api/v1/auth/connect error handling."""

    def test_connect_auth_error_returns_401(self, client, valid_headers):
        """POST /connect returns 401 on GarminConnectAuthenticationError."""
        from garminconnect import GarminConnectAuthenticationError

        with patch(
            "src.api.routers.auth_garmin.Garmin",
            side_effect=GarminConnectAuthenticationError("bad creds"),
        ):
            response = client.post(
                "/api/v1/auth/connect",
                json={
                    "email": "bad@runner.com",
                    "password": "wrong",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        assert response.status_code == 401
        assert "Garmin authentication failed" in response.json()["detail"]

    def test_connect_generic_error_returns_502(self, client, valid_headers):
        """POST /connect returns 502 on unexpected exceptions during Garmin login."""
        with patch(
            "src.api.routers.auth_garmin.Garmin",
            side_effect=ConnectionError("network error"),
        ):
            response = client.post(
                "/api/v1/auth/connect",
                json={
                    "email": "trail@runner.com",
                    "password": "secret",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        assert response.status_code == 502
        assert "Failed to connect to Garmin" in response.json()["detail"]

    def test_connect_missing_token_key_returns_500(self, client, valid_headers):
        """POST /connect returns 500 if GARMIN_TOKEN_KEY env var is not set."""
        del os.environ["GARMIN_TOKEN_KEY"]

        response = client.post(
            "/api/v1/auth/connect",
            json={
                "email": "trail@runner.com",
                "password": "secret",
                "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
            },
            headers=valid_headers,
        )

        # Restore key for subsequent tests
        os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()

        assert response.status_code == 500
        assert "Token encryption not configured" in response.json()["detail"]

    def test_connect_without_api_key_returns_401(self, client):
        """POST /connect without X-API-Key header returns 401."""
        response = client.post(
            "/api/v1/auth/connect",
            json={
                "email": "trail@runner.com",
                "password": "secret",
                "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
            },
        )
        assert response.status_code == 401

    def test_connect_with_invalid_api_key_returns_401(self, client, invalid_headers):
        """POST /connect with wrong API key returns 401."""
        response = client.post(
            "/api/v1/auth/connect",
            json={
                "email": "trail@runner.com",
                "password": "secret",
                "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
            },
            headers=invalid_headers,
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /connect/mfa
# ---------------------------------------------------------------------------


class TestConnectMfaEndpoint:
    """Tests for POST /api/v1/auth/connect/mfa."""

    def _seed_mfa_session(self, session_id: str, better_auth_user_id: str, mock_garmin=None):
        """Helper to inject a valid MFA session directly into the store."""
        from src.api.routers.auth_garmin import _mfa_sessions

        if mock_garmin is None:
            mock_garmin = _make_mock_garmin()

        _mfa_sessions[session_id] = {
            "client_state": {"state": "pending"},
            "email": "mfa@runner.com",
            "better_auth_user_id": better_auth_user_id,
            "garmin_client": mock_garmin,
            "existing_user_id": None,
            "created": time.time(),
        }

    def test_mfa_success_returns_connected(self, client, valid_headers, mock_db):
        """POST /connect/mfa returns connected=True when MFA code is correct."""
        session_id = "test-session-uuid-001"
        mock_garmin = _make_mock_garmin("MfaRunner")
        self._seed_mfa_session(session_id, TEST_BETTER_AUTH_USER_ID, mock_garmin)

        fake_oauth1 = MagicMock()
        fake_oauth2 = MagicMock()

        with patch("src.api.routers.auth_garmin.garth") as mock_garth:
            mock_garth.sso.resume_login = MagicMock(return_value=(fake_oauth1, fake_oauth2))

            response = client.post(
                "/api/v1/auth/connect/mfa",
                json={
                    "mfa_session_id": session_id,
                    "mfa_code": "123456",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is True
        assert body["needs_mfa"] is False

    def test_mfa_expired_session_returns_400(self, client, valid_headers):
        """POST /connect/mfa returns 400 if session_id is not found or expired."""
        response = client.post(
            "/api/v1/auth/connect/mfa",
            json={
                "mfa_session_id": "nonexistent-session-id",
                "mfa_code": "123456",
                "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
            },
            headers=valid_headers,
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    def test_mfa_user_mismatch_returns_403(self, client, valid_headers):
        """POST /connect/mfa returns 403 if better_auth_user_id does not match session."""
        session_id = "test-session-uuid-002"
        self._seed_mfa_session(session_id, "original-user-id")

        response = client.post(
            "/api/v1/auth/connect/mfa",
            json={
                "mfa_session_id": session_id,
                "mfa_code": "123456",
                "better_auth_user_id": "different-user-id",
            },
            headers=valid_headers,
        )

        assert response.status_code == 403
        assert "does not match" in response.json()["detail"].lower()

    def test_mfa_wrong_code_returns_401(self, client, valid_headers):
        """POST /connect/mfa returns 401 if the MFA code verification fails."""
        session_id = "test-session-uuid-003"
        self._seed_mfa_session(session_id, TEST_BETTER_AUTH_USER_ID)

        with patch("src.api.routers.auth_garmin.garth") as mock_garth:
            mock_garth.sso.resume_login = MagicMock(side_effect=Exception("wrong code"))

            response = client.post(
                "/api/v1/auth/connect/mfa",
                json={
                    "mfa_session_id": session_id,
                    "mfa_code": "000000",
                    "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
                },
                headers=valid_headers,
            )

        assert response.status_code == 401
        assert "MFA verification failed" in response.json()["detail"]

    def test_mfa_missing_token_key_returns_500(self, client, valid_headers):
        """POST /connect/mfa returns 500 if GARMIN_TOKEN_KEY is absent."""
        del os.environ["GARMIN_TOKEN_KEY"]

        response = client.post(
            "/api/v1/auth/connect/mfa",
            json={
                "mfa_session_id": "any-session",
                "mfa_code": "123456",
                "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
            },
            headers=valid_headers,
        )

        os.environ["GARMIN_TOKEN_KEY"] = TokenManager.generate_key()
        assert response.status_code == 500

    def test_mfa_without_api_key_returns_401(self, client):
        """POST /connect/mfa without API key returns 401."""
        response = client.post(
            "/api/v1/auth/connect/mfa",
            json={
                "mfa_session_id": "some-session",
                "mfa_code": "123456",
                "better_auth_user_id": TEST_BETTER_AUTH_USER_ID,
            },
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


class TestGarminStatus:
    """Tests for GET /api/v1/auth/status."""

    def test_status_not_connected_when_no_user(self, client, valid_headers, mock_db):
        """GET /status returns connected=False when no garmin account is linked."""
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=None)

        response = client.get(
            "/api/v1/auth/status",
            params={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is False
        assert body["garmin_display_name"] is None
        assert body["user_id"] is None

    def test_status_not_connected_when_no_tokens(self, client, valid_headers, mock_db):
        """GET /status returns connected=False when user exists but has no tokens."""
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=TEST_USER_ID)
        mock_db.get_user_info = AsyncMock(return_value={"encrypted_tokens": None, "display_name": "Test"})

        response = client.get(
            "/api/v1/auth/status",
            params={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is False
        assert body["user_id"] == TEST_USER_ID

    def test_status_connected_returns_display_name_and_user_id(self, client, valid_headers, mock_db):
        """GET /status returns connected=True with display_name when fully connected."""
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=TEST_USER_ID)
        mock_db.get_user_info = AsyncMock(return_value={
            "encrypted_tokens": "encrypted-blob",
            "display_name": "TrailRunner42",
        })
        mock_db.query_sync_status = AsyncMock(return_value=[])

        response = client.get(
            "/api/v1/auth/status",
            params={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is True
        assert body["garmin_display_name"] == "TrailRunner42"
        assert body["user_id"] == TEST_USER_ID

    def test_status_connected_includes_last_sync_timestamp(self, client, valid_headers, mock_db):
        """GET /status includes last_sync when sync rows exist."""
        from datetime import datetime, timezone

        ts = datetime(2026, 3, 4, 6, 0, 0, tzinfo=timezone.utc)
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=TEST_USER_ID)
        mock_db.get_user_info = AsyncMock(return_value={
            "encrypted_tokens": "blob",
            "display_name": "Runner",
        })
        mock_db.query_sync_status = AsyncMock(return_value=[
            {"last_sync_timestamp": ts, "category": "activities"},
        ])

        response = client.get(
            "/api/v1/auth/status",
            params={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is True
        assert body["last_sync"] is not None
        assert "2026-03-04" in body["last_sync"]

    def test_status_without_api_key_returns_401(self, client):
        """GET /status without API key returns 401."""
        response = client.get(
            "/api/v1/auth/status",
            params={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
        )
        assert response.status_code == 401

    def test_status_with_invalid_api_key_returns_401(self, client, invalid_headers):
        """GET /status with wrong API key returns 401."""
        response = client.get(
            "/api/v1/auth/status",
            params={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=invalid_headers,
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /disconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    """Tests for POST /api/v1/auth/disconnect."""

    def test_disconnect_success(self, client, valid_headers, mock_db):
        """POST /disconnect returns {disconnected: true} when account is linked."""
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=TEST_USER_ID)

        response = client.post(
            "/api/v1/auth/disconnect",
            json={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=valid_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["disconnected"] is True
        mock_db.unlink_better_auth_user.assert_called_once_with(TEST_USER_ID)

    def test_disconnect_no_linked_account_returns_404(self, client, valid_headers, mock_db):
        """POST /disconnect returns 404 when no Garmin account is linked."""
        mock_db.get_user_by_better_auth_id = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/auth/disconnect",
            json={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=valid_headers,
        )

        assert response.status_code == 404
        assert "No Garmin account linked" in response.json()["detail"]

    def test_disconnect_without_api_key_returns_401(self, client):
        """POST /disconnect without API key returns 401."""
        response = client.post(
            "/api/v1/auth/disconnect",
            json={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
        )
        assert response.status_code == 401

    def test_disconnect_with_invalid_api_key_returns_401(self, client, invalid_headers):
        """POST /disconnect with wrong API key returns 401."""
        response = client.post(
            "/api/v1/auth/disconnect",
            json={"better_auth_user_id": TEST_BETTER_AUTH_USER_ID},
            headers=invalid_headers,
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# _cleanup_expired_mfa()
# ---------------------------------------------------------------------------


class TestCleanupExpiredMfa:
    """Unit tests for the _cleanup_expired_mfa helper."""

    def test_cleanup_removes_expired_sessions(self):
        """_cleanup_expired_mfa removes sessions older than the 600s TTL."""
        from src.api.routers.auth_garmin import _mfa_sessions, _cleanup_expired_mfa

        old_time = time.time() - 601  # 601 seconds ago → past the 600s TTL
        _mfa_sessions["old-session"] = {
            "created": old_time,
            "email": "old@test.com",
            "better_auth_user_id": "user-1",
            "garmin_client": None,
            "client_state": {},
            "existing_user_id": None,
        }
        _mfa_sessions["fresh-session"] = {
            "created": time.time(),
            "email": "fresh@test.com",
            "better_auth_user_id": "user-2",
            "garmin_client": None,
            "client_state": {},
            "existing_user_id": None,
        }

        _cleanup_expired_mfa()

        assert "old-session" not in _mfa_sessions
        assert "fresh-session" in _mfa_sessions

    def test_cleanup_leaves_non_expired_sessions(self):
        """_cleanup_expired_mfa keeps sessions within the 300-second TTL."""
        from src.api.routers.auth_garmin import _mfa_sessions, _cleanup_expired_mfa

        _mfa_sessions["young-session"] = {
            "created": time.time() - 100,  # 100s ago → still valid
            "email": "young@test.com",
            "better_auth_user_id": "user-3",
            "garmin_client": None,
            "client_state": {},
            "existing_user_id": None,
        }

        _cleanup_expired_mfa()

        assert "young-session" in _mfa_sessions

    def test_cleanup_handles_empty_store(self):
        """_cleanup_expired_mfa does not raise on an empty session store."""
        from src.api.routers.auth_garmin import _mfa_sessions, _cleanup_expired_mfa

        _mfa_sessions.clear()
        _cleanup_expired_mfa()  # Should not raise
        assert _mfa_sessions == {}
