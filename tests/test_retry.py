"""Tests for src/utils/retry.py safe_api_call decorator and create_retry_decorator."""

import pytest
from unittest.mock import MagicMock, patch

from tenacity import RetryError
from garminconnect import GarminConnectTooManyRequestsError, GarminConnectConnectionError
from garth.exc import GarthHTTPError

from src.utils.retry import safe_api_call, create_retry_decorator, RETRYABLE_EXCEPTIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _garth_http_error(status_code: int) -> GarthHTTPError:
    """Create a GarthHTTPError whose string representation contains the status code.

    retry.py detects status codes by checking 'NNN' in str(e), because the
    GarthHTTPError.msg field is included in __str__.
    """
    mock_error = MagicMock()
    return GarthHTTPError(msg=f"{status_code} HTTP Error", error=mock_error)


def _retry_error() -> RetryError:
    """Create a minimal RetryError with a mock last_attempt."""
    mock_future = MagicMock()
    mock_future.exception.return_value = RuntimeError("retried out")
    return RetryError(last_attempt=mock_future)


# ---------------------------------------------------------------------------
# safe_api_call — success path
# ---------------------------------------------------------------------------


class TestSafeApiCallSuccess:
    """Tests for safe_api_call when the wrapped function succeeds."""

    def test_returns_true_success_flag_on_success(self):
        """Wrapped function returns (True, result, None) on success."""

        @safe_api_call
        def my_func():
            return 42

        success, result, error = my_func()
        assert success is True

    def test_returns_correct_result_on_success(self):
        """Result field contains the function's return value."""

        @safe_api_call
        def my_func():
            return {"data": "value"}

        _, result, _ = my_func()
        assert result == {"data": "value"}

    def test_returns_none_error_on_success(self):
        """Error field is None when function succeeds."""

        @safe_api_call
        def my_func():
            return "ok"

        _, _, error = my_func()
        assert error is None

    def test_passes_args_and_kwargs_to_wrapped_function(self):
        """Arguments and keyword arguments are forwarded to the wrapped function."""

        @safe_api_call
        def add(a, b, *, multiplier=1):
            return (a + b) * multiplier

        success, result, error = add(3, 4, multiplier=2)
        assert success is True
        assert result == 14
        assert error is None

    def test_preserves_function_name_via_wraps(self):
        """safe_api_call preserves the original function name (uses @wraps)."""

        @safe_api_call
        def my_named_function():
            return None

        assert my_named_function.__name__ == "my_named_function"


# ---------------------------------------------------------------------------
# safe_api_call — GarthHTTPError handling
# ---------------------------------------------------------------------------


class TestSafeApiCallGarthHTTPError:
    """Tests for safe_api_call handling of GarthHTTPError at various status codes."""

    def test_catches_garth_http_error_400(self):
        """GarthHTTPError with 400 status returns (False, None, msg) with 400 info."""

        @safe_api_call
        def my_func():
            raise _garth_http_error(400)

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None
        assert "400" in error

    def test_catches_garth_http_error_401(self):
        """GarthHTTPError with 401 status returns (False, None, msg) with auth info."""

        @safe_api_call
        def my_func():
            raise _garth_http_error(401)

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None
        assert "401" in error

    def test_catches_garth_http_error_403(self):
        """GarthHTTPError with 403 status returns (False, None, msg) with access info."""

        @safe_api_call
        def my_func():
            raise _garth_http_error(403)

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None
        assert "403" in error

    def test_catches_garth_http_error_429(self):
        """GarthHTTPError with 429 status returns (False, None, msg) with rate limit info."""

        @safe_api_call
        def my_func():
            raise _garth_http_error(429)

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None
        assert "429" in error

    def test_catches_garth_http_error_500(self):
        """GarthHTTPError with 500 status returns (False, None, msg) with server error info."""

        @safe_api_call
        def my_func():
            raise _garth_http_error(500)

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None
        assert "500" in error

    def test_garth_http_error_returns_false_not_raises(self):
        """GarthHTTPError does not propagate — it is caught and returned as False."""

        @safe_api_call
        def my_func():
            raise _garth_http_error(404)

        # Should not raise
        success, result, error = my_func()
        assert success is False


# ---------------------------------------------------------------------------
# safe_api_call — GarminConnect exceptions
# ---------------------------------------------------------------------------


class TestSafeApiCallGarminConnectErrors:
    """Tests for safe_api_call handling of garminconnect-specific exceptions."""

    def test_catches_garmin_connect_too_many_requests(self):
        """GarminConnectTooManyRequestsError returns (False, None, msg)."""

        @safe_api_call
        def my_func():
            raise GarminConnectTooManyRequestsError("Too many requests")

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None

    def test_catches_garmin_connect_connection_error(self):
        """GarminConnectConnectionError returns (False, None, msg)."""

        @safe_api_call
        def my_func():
            raise GarminConnectConnectionError("Connection refused")

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None

    def test_catches_retry_error(self):
        """tenacity.RetryError returns (False, None, msg)."""

        @safe_api_call
        def my_func():
            raise _retry_error()

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None
        assert "retri" in error.lower()

    def test_catches_unexpected_exception(self):
        """Any unexpected Exception returns (False, None, msg) without propagating."""

        @safe_api_call
        def my_func():
            raise ValueError("Something unexpected")

        success, result, error = my_func()
        assert success is False
        assert result is None
        assert error is not None
        assert "ValueError" in error

    def test_too_many_requests_error_message_includes_rate_limit(self):
        """Error message for GarminConnectTooManyRequestsError mentions rate limit."""

        @safe_api_call
        def my_func():
            raise GarminConnectTooManyRequestsError("Rate limit hit")

        _, _, error = my_func()
        assert error is not None
        # The message should mention rate-limit context
        assert "Rate limit" in error or "rate limit" in error.lower()

    def test_connection_error_message_mentions_connection(self):
        """Error message for GarminConnectConnectionError mentions connection."""

        @safe_api_call
        def my_func():
            raise GarminConnectConnectionError("No route to host")

        _, _, error = my_func()
        assert error is not None
        assert "Connection" in error or "connection" in error.lower()


# ---------------------------------------------------------------------------
# create_retry_decorator
# ---------------------------------------------------------------------------


class TestCreateRetryDecorator:
    """Tests for the create_retry_decorator factory function."""

    def test_create_retry_decorator_returns_callable(self):
        """create_retry_decorator returns a decorator (callable)."""
        decorator = create_retry_decorator(max_attempts=2)
        assert callable(decorator)

    def test_retry_decorator_can_wrap_function(self):
        """Decorator returned by create_retry_decorator can be applied to a function."""
        decorator = create_retry_decorator(max_attempts=2, min_wait=0, max_wait=0)

        @decorator
        def my_func():
            return "ok"

        result = my_func()
        assert result == "ok"

    def test_retry_decorator_custom_max_attempts(self):
        """Decorator retries up to max_attempts before re-raising."""
        call_count = 0
        decorator = create_retry_decorator(
            max_attempts=3,
            min_wait=0,
            max_wait=0,
            exceptions=(GarminConnectConnectionError,),
        )

        @decorator
        def my_func():
            nonlocal call_count
            call_count += 1
            raise GarminConnectConnectionError("fail")

        with pytest.raises(GarminConnectConnectionError):
            my_func()

        assert call_count == 3

    def test_retry_decorator_does_not_retry_non_retryable_exception(self):
        """Decorator does not retry exceptions not in the retryable list."""
        call_count = 0
        decorator = create_retry_decorator(
            max_attempts=3,
            min_wait=0,
            max_wait=0,
            exceptions=(GarminConnectConnectionError,),
        )

        @decorator
        def my_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            my_func()

        # Should only be called once — no retry for ValueError
        assert call_count == 1

    def test_default_retryable_exceptions_tuple_is_not_empty(self):
        """RETRYABLE_EXCEPTIONS constant is a non-empty tuple of exception types."""
        assert isinstance(RETRYABLE_EXCEPTIONS, tuple)
        assert len(RETRYABLE_EXCEPTIONS) > 0
        for exc_class in RETRYABLE_EXCEPTIONS:
            assert issubclass(exc_class, BaseException)
