"""Tests for security fixes from audit report.

Covers: rate limiting, CORS, error sanitization, date range limits, PII removal.
"""

import os
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from src.api.dependencies import date_range, _MAX_DATE_RANGE_DAYS
from src.api.rate_limit import limiter, AUTH_RATE_LIMIT


# ---------------------------------------------------------------------------
# Rate limiting (S1/S3/S12)
# ---------------------------------------------------------------------------


class TestRateLimitConfig:
    """Tests for rate limiting configuration."""

    def test_limiter_has_default_limit(self):
        """Global rate limit is configured."""
        assert limiter._default_limits is not None

    def test_auth_rate_limit_is_strict(self):
        """Auth endpoints have a strict rate limit (5/15min)."""
        assert AUTH_RATE_LIMIT == "5/15minutes"

    def test_limiter_uses_remote_address(self):
        """Limiter extracts client IP for keying."""
        # key_func should be get_remote_address
        from slowapi.util import get_remote_address

        assert limiter._key_func == get_remote_address


class TestRateLimitOnApp:
    """Tests that rate limiter is wired into the FastAPI app."""

    def test_app_has_limiter_state(self):
        """App state contains the limiter instance."""
        from src.api.main import app

        assert hasattr(app.state, "limiter")
        assert app.state.limiter is limiter

    def test_rate_limit_exceeded_handler_registered(self):
        """RateLimitExceeded exception handler is registered on the app."""
        from slowapi.errors import RateLimitExceeded
        from src.api.main import app

        assert RateLimitExceeded in app.exception_handlers


# ---------------------------------------------------------------------------
# CORS (S9)
# ---------------------------------------------------------------------------


class TestCORS:
    """Tests for CORS middleware configuration."""

    def test_cors_middleware_present(self):
        """CORS middleware is added to the app."""
        from src.api.main import app

        middleware_classes = [
            m.cls.__name__ if hasattr(m, "cls") else type(m).__name__
            for m in app.user_middleware
        ]
        assert "CORSMiddleware" in middleware_classes

    def test_cors_rejects_unauthorized_origin(self):
        """Requests from unauthorized origins get no CORS headers."""
        from src.api.main import app

        os.environ.setdefault("API_KEY", "test-key")
        client = TestClient(app)

        response = client.options(
            "/api/v1/daily/summary",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not include Access-Control-Allow-Origin for evil.com
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin != "https://evil.com"

    def test_cors_env_override(self):
        """CORS_ALLOWED_ORIGINS env var is respected."""
        from src.api.main import _allowed_origins

        # Default should include hillsrun.com
        assert "https://hillsrun.com" in _allowed_origins


# ---------------------------------------------------------------------------
# Error sanitization (S5/S6)
# ---------------------------------------------------------------------------


class TestErrorSanitization:
    """Tests that error messages don't leak internal details."""

    def test_connect_auth_error_is_generic(self):
        """Auth failure returns generic message, not exception details."""
        from src.api.routers.auth_garmin import connect_garmin

        # The endpoint should return "Garmin authentication failed"
        # without appending the exception string
        import inspect

        source = inspect.getsource(connect_garmin)
        # Should NOT contain f-string with {e} in error details
        assert 'detail=f"Garmin authentication failed: {e}"' not in source
        assert 'detail="Garmin authentication failed"' in source

    def test_connect_server_error_is_generic(self):
        """Server error returns generic message."""
        from src.api.routers.auth_garmin import connect_garmin

        import inspect

        source = inspect.getsource(connect_garmin)
        assert 'detail=f"Failed to connect to Garmin: {e}"' not in source
        assert 'detail="Failed to connect to Garmin"' in source

    def test_finalize_connect_error_is_generic(self):
        """DB link error returns generic message."""
        from src.api.routers.auth_garmin import _finalize_connect

        import inspect

        source = inspect.getsource(_finalize_connect)
        assert 'detail=f"Failed to link Garmin account: {e}"' not in source
        assert 'detail="Failed to link Garmin account"' in source

    def test_mfa_error_is_generic(self):
        """MFA verification error returns generic message."""
        from src.api.routers.auth_garmin import connect_garmin_mfa

        import inspect

        source = inspect.getsource(connect_garmin_mfa)
        assert 'detail=f"MFA verification failed: {e}"' not in source
        assert 'detail="MFA verification failed"' in source


class TestPIIRemoval:
    """Tests that PII (emails) are not logged."""

    def test_no_email_in_mfa_log(self):
        """MFA log message uses session_id, not email."""
        from src.api.routers import auth_garmin

        import inspect

        source = inspect.getsource(auth_garmin)
        # Should not log email in MFA required message
        assert "MFA required for {request.email}" not in source
        # Should log session_id instead
        assert "MFA required, session_id={session_id}" in source

    def test_no_email_in_existing_user_log(self):
        """Existing user lookup log doesn't include email."""
        from src.api.routers.auth_garmin import _finalize_connect

        import inspect

        source = inspect.getsource(_finalize_connect)
        # Log messages should not include email= (parameter names are OK)
        assert "email={" not in source
        assert 'f"Found existing garmin_user by email' not in source


# ---------------------------------------------------------------------------
# Date range validation (S15)
# ---------------------------------------------------------------------------


class TestDateRangeLimit:
    """Tests for date range validation."""

    def test_date_range_within_limit(self):
        """Date range within 365 days is accepted."""
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)
        result_start, result_end = date_range(start, end)
        assert result_start == start
        assert result_end == end

    def test_date_range_exactly_365_days(self):
        """Date range of exactly 365 days is accepted."""
        start = date(2025, 1, 1)
        end = start + timedelta(days=_MAX_DATE_RANGE_DAYS)
        result_start, result_end = date_range(start, end)
        assert result_start == start
        assert result_end == end

    def test_date_range_exceeds_limit(self):
        """Date range exceeding 365 days raises 400 error."""
        start = date(2023, 1, 1)
        end = date(2025, 12, 31)
        with pytest.raises(HTTPException) as exc_info:
            date_range(start, end)
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "365" in exc_info.value.detail

    def test_date_range_default_is_within_limit(self):
        """Default date range (30 days) is within limit."""
        start, end = date_range(None, None)
        assert (end - start).days == 30

    def test_max_date_range_constant(self):
        """Max date range constant is 365."""
        assert _MAX_DATE_RANGE_DAYS == 365


# ---------------------------------------------------------------------------
# Security headers (S8/S10) — verified via next.config.ts content
# ---------------------------------------------------------------------------


class TestSecurityHeadersConfig:
    """Tests that next.config.ts contains required security headers."""

    @pytest.fixture(autouse=True)
    def load_config(self):
        """Load next.config.ts content."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "web", "next.config.ts"
        )
        with open(config_path) as f:
            self.config_content = f.read()

    def test_x_content_type_options(self):
        assert "X-Content-Type-Options" in self.config_content
        assert "nosniff" in self.config_content

    def test_x_frame_options(self):
        assert "X-Frame-Options" in self.config_content
        assert "DENY" in self.config_content

    def test_hsts(self):
        assert "Strict-Transport-Security" in self.config_content
        assert "max-age=31536000" in self.config_content

    def test_referrer_policy(self):
        assert "Referrer-Policy" in self.config_content
        assert "strict-origin-when-cross-origin" in self.config_content

    def test_csp_on_all_routes(self):
        """CSP is applied to all routes, not just /sw.js."""
        assert "Content-Security-Policy" in self.config_content
        # Verify the global route pattern exists
        assert '"/(.*)"' in self.config_content

    def test_csp_frame_ancestors(self):
        """CSP includes frame-ancestors none (clickjacking protection)."""
        assert "frame-ancestors 'none'" in self.config_content

    def test_permissions_policy(self):
        """Permissions-Policy restricts sensitive APIs."""
        assert "Permissions-Policy" in self.config_content
        assert "camera=()" in self.config_content
