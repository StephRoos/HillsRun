"""Tests for GarminClient and the safe_api_call / retry_api_call decorators."""

import json
import time
import pytest
from datetime import date
from unittest.mock import MagicMock, patch, call

from garminconnect import GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError
from garth.exc import GarthHTTPError
from tenacity import RetryError

from src.config import GarminConfig
from src.garmin_client import GarminClient
from src.token_manager import TokenManager
from src.utils.retry import safe_api_call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_garth_http_error(status_code: int) -> GarthHTTPError:
    """Build a GarthHTTPError whose .error.status_code equals status_code.

    GarthHTTPError is a dataclass with msg (str) and error (response object).
    """
    response = MagicMock()
    response.status_code = status_code
    return GarthHTTPError(msg=f"HTTP {status_code} error", error=response)


# ---------------------------------------------------------------------------
# TestGarminClientInit
# ---------------------------------------------------------------------------

class TestGarminClientInit:
    """Tests for GarminClient.__init__."""

    def test_stores_config(self, test_garmin_config):
        """__init__ stores the provided GarminConfig on self.config."""
        client = GarminClient(test_garmin_config)
        assert client.config is test_garmin_config

    def test_default_rate_limit_delay(self, test_garmin_config):
        """Default rate_limit_delay is 0.5 seconds."""
        client = GarminClient(test_garmin_config)
        assert client.rate_limit_delay == 0.5

    def test_custom_rate_limit_delay(self, test_garmin_config):
        """Custom rate_limit_delay is stored correctly."""
        client = GarminClient(test_garmin_config, rate_limit_delay=1.2)
        assert client.rate_limit_delay == 1.2

    def test_client_is_none_initially(self, test_garmin_config):
        """The inner Garmin client is None before connect() is called."""
        client = GarminClient(test_garmin_config)
        assert client.client is None

    def test_last_request_time_is_zero(self, test_garmin_config):
        """_last_request_time starts at 0.0."""
        client = GarminClient(test_garmin_config)
        assert client._last_request_time == 0.0


# ---------------------------------------------------------------------------
# TestGarminClientConnect
# ---------------------------------------------------------------------------

class TestGarminClientConnect:
    """Tests for GarminClient.connect()."""

    def test_connect_success(self, test_garmin_config):
        """connect() loads tokens, creates the Garmin client, and sets display_name."""
        mock_garth_client = MagicMock()
        mock_garth_client.profile = {
            "displayName": "testuser",
            "fullName": "Test User",
        }

        with patch("src.garmin_client.garth.Client", return_value=mock_garth_client) as mock_garth_cls, \
             patch("src.garmin_client.Garmin") as mock_garmin_cls:

            mock_garmin_instance = MagicMock()
            mock_garmin_cls.return_value = mock_garmin_instance

            gc = GarminClient(test_garmin_config)
            gc.connect()

            # garth.Client().load() must be called with the tokens directory
            mock_garth_client.load.assert_called_once_with(str(test_garmin_config.tokens_dir))

            # The inner Garmin instance must be assigned
            assert gc.client is mock_garmin_instance

            # display_name and full_name must be set from the profile
            assert mock_garmin_instance.display_name == "testuser"
            assert mock_garmin_instance.full_name == "Test User"

    def test_connect_missing_tokens_raises_auth_error(self, test_garmin_config):
        """connect() raises GarminConnectAuthenticationError when tokens are absent."""
        mock_garth_client = MagicMock()
        mock_garth_client.load.side_effect = FileNotFoundError("no tokens")

        with patch("src.garmin_client.garth.Client", return_value=mock_garth_client):
            gc = GarminClient(test_garmin_config)
            with pytest.raises(GarminConnectAuthenticationError):
                gc.connect()

    def test_connect_general_exception_propagates(self, test_garmin_config):
        """connect() re-raises unexpected exceptions unchanged."""
        mock_garth_client = MagicMock()
        mock_garth_client.load.side_effect = RuntimeError("unexpected failure")

        with patch("src.garmin_client.garth.Client", return_value=mock_garth_client):
            gc = GarminClient(test_garmin_config)
            with pytest.raises(RuntimeError, match="unexpected failure"):
                gc.connect()


# ---------------------------------------------------------------------------
# TestRateLimit
# ---------------------------------------------------------------------------

class TestRateLimit:
    """Tests for GarminClient._rate_limit()."""

    def test_applies_delay_when_too_fast(self, test_garmin_config):
        """_rate_limit() sleeps when called again within rate_limit_delay."""
        gc = GarminClient(test_garmin_config, rate_limit_delay=0.5)
        # Simulate a recent request only 0.1 seconds ago
        gc._last_request_time = time.time() - 0.1

        with patch("src.garmin_client.time.sleep") as mock_sleep:
            gc._rate_limit()
            # sleep should have been called with a positive duration ~0.4 s
            mock_sleep.assert_called_once()
            sleep_arg = mock_sleep.call_args[0][0]
            assert sleep_arg > 0
            assert sleep_arg <= 0.5

    def test_no_delay_when_enough_time_passed(self, test_garmin_config):
        """_rate_limit() does NOT sleep when sufficient time has already passed."""
        gc = GarminClient(test_garmin_config, rate_limit_delay=0.5)
        # Simulate a request from 2 seconds ago (well past the 0.5 s threshold)
        gc._last_request_time = time.time() - 2.0

        with patch("src.garmin_client.time.sleep") as mock_sleep:
            gc._rate_limit()
            mock_sleep.assert_not_called()

    def test_updates_last_request_time(self, test_garmin_config):
        """_rate_limit() updates _last_request_time after the call."""
        gc = GarminClient(test_garmin_config, rate_limit_delay=0.0)
        before = time.time()
        gc._rate_limit()
        after = time.time()
        assert before <= gc._last_request_time <= after


# ---------------------------------------------------------------------------
# TestFromEncryptedTokens
# ---------------------------------------------------------------------------

class TestFromEncryptedTokens:
    """Tests for GarminClient.from_encrypted_tokens() classmethod."""

    def test_creates_client_from_encrypted_data(self, test_garmin_config):
        """from_encrypted_tokens() decrypts tokens and returns a connected GarminClient."""
        token_key = test_garmin_config.token_key
        # Create real encrypted token data using TokenManager
        token_data = json.dumps({"access_token": "abc", "refresh_token": "xyz"})
        tm = TokenManager(token_key)
        encrypted = tm.encrypt(token_data)

        mock_garth_client = MagicMock()
        mock_garth_client.profile = {"displayName": "dbuser", "fullName": "DB User"}

        with patch("src.garmin_client.garth.Client", return_value=mock_garth_client) as mock_garth_cls, \
             patch("src.garmin_client.Garmin") as mock_garmin_cls:

            mock_garmin_instance = MagicMock()
            mock_garmin_cls.return_value = mock_garmin_instance

            instance = GarminClient.from_encrypted_tokens(encrypted, token_key)

            # Must be a GarminClient
            assert isinstance(instance, GarminClient)

            # garth_client.loads() must have been called with the decrypted JSON
            mock_garth_client.loads.assert_called_once_with(token_data)

            # display_name set from profile
            assert mock_garmin_instance.display_name == "dbuser"

            # rate_limit_delay default
            assert instance.rate_limit_delay == 0.5

    def test_custom_rate_limit_delay_from_encrypted(self, test_garmin_config):
        """from_encrypted_tokens() forwards rate_limit_delay to the new instance."""
        token_key = test_garmin_config.token_key
        token_data = json.dumps({"access_token": "abc"})
        tm = TokenManager(token_key)
        encrypted = tm.encrypt(token_data)

        mock_garth_client = MagicMock()
        mock_garth_client.profile = {"displayName": "u", "fullName": "U"}

        with patch("src.garmin_client.garth.Client", return_value=mock_garth_client), \
             patch("src.garmin_client.Garmin"):

            instance = GarminClient.from_encrypted_tokens(encrypted, token_key, rate_limit_delay=1.5)
            assert instance.rate_limit_delay == 1.5


# ---------------------------------------------------------------------------
# TestGetRefreshedTokens
# ---------------------------------------------------------------------------

class TestGetRefreshedTokens:
    """Tests for GarminClient.get_refreshed_tokens()."""

    def test_returns_string(self, test_garmin_config):
        """get_refreshed_tokens() returns a string (JSON export from garth)."""
        gc = GarminClient(test_garmin_config)
        gc.client = MagicMock()
        gc.client.garth.dumps.return_value = '{"access_token": "new_token"}'

        result = gc.get_refreshed_tokens()

        assert isinstance(result, str)
        gc.client.garth.dumps.assert_called_once()

    def test_returns_garth_dumps_output(self, test_garmin_config):
        """get_refreshed_tokens() returns exactly what garth.dumps() produces."""
        gc = GarminClient(test_garmin_config)
        gc.client = MagicMock()
        expected = '{"some": "token_data"}'
        gc.client.garth.dumps.return_value = expected

        assert gc.get_refreshed_tokens() == expected


# ---------------------------------------------------------------------------
# TestSafeApiCallDecorator
# ---------------------------------------------------------------------------

class TestSafeApiCallDecorator:
    """Unit tests for the safe_api_call decorator in isolation."""

    # --- Success path ---

    def test_success_returns_true_result_none(self):
        """A successful call returns (True, result, None)."""
        @safe_api_call
        def my_func():
            return {"data": 42}

        ok, result, err = my_func()
        assert ok is True
        assert result == {"data": 42}
        assert err is None

    def test_success_with_args(self):
        """safe_api_call passes positional and keyword arguments through."""
        @safe_api_call
        def add(a, b, *, factor=1):
            return (a + b) * factor

        ok, result, err = add(3, 4, factor=2)
        assert ok is True
        assert result == 14
        assert err is None

    # --- GarthHTTPError status codes ---

    @pytest.mark.parametrize("status_code, expected_fragment", [
        (400, "400"),
        (401, "401"),
        (403, "403"),
        (404, "404"),
        (429, "429"),
        (500, "500"),
        (503, "503"),
    ])
    def test_garth_http_error_returns_false_with_message(self, status_code, expected_fragment):
        """GarthHTTPError is caught and mapped to (False, None, descriptive_msg)."""
        exc = _make_garth_http_error(status_code)

        @safe_api_call
        def failing():
            raise exc

        ok, result, err = failing()
        assert ok is False
        assert result is None
        assert err is not None
        assert expected_fragment in err

    def test_garth_http_error_unknown_status(self):
        """An unmapped status code falls through to the generic HTTP error message."""
        response = MagicMock()
        response.status_code = 418  # I'm a teapot
        try:
            err_obj = GarthHTTPError(response, "teapot")
        except TypeError:
            err_obj = GarthHTTPError.__new__(GarthHTTPError)
            err_obj.response = response
            err_obj.args = ("teapot",)

        @safe_api_call
        def failing():
            raise err_obj

        ok, result, error_msg = failing()
        assert ok is False
        assert result is None
        # Generic branch includes the status code
        assert "418" in error_msg or "HTTP error" in error_msg

    # --- GarminConnectTooManyRequestsError ---

    def test_too_many_requests_returns_false(self):
        """GarminConnectTooManyRequestsError returns (False, None, msg)."""
        @safe_api_call
        def failing():
            raise GarminConnectTooManyRequestsError("too many")

        ok, result, err = failing()
        assert ok is False
        assert result is None
        assert err is not None
        assert "Rate limit" in err or "rate limit" in err.lower() or "too many" in err.lower()

    # --- GarminConnectConnectionError ---

    def test_connection_error_returns_false(self):
        """GarminConnectConnectionError returns (False, None, msg)."""
        @safe_api_call
        def failing():
            raise GarminConnectConnectionError("no conn")

        ok, result, err = failing()
        assert ok is False
        assert result is None
        assert err is not None
        assert "Connection error" in err or "connection" in err.lower()

    # --- RetryError ---

    def test_retry_error_returns_false(self):
        """tenacity RetryError (max retries exceeded) returns (False, None, msg)."""
        # RetryError wraps a future; we create a minimal version.
        inner = MagicMock()
        inner.exception.return_value = GarminConnectConnectionError("timeout")

        @safe_api_call
        def failing():
            raise RetryError(inner)

        ok, result, err = failing()
        assert ok is False
        assert result is None
        assert err is not None
        assert "retries" in err.lower() or "retry" in err.lower() or "Max" in err

    # --- Unexpected exception ---

    def test_unexpected_exception_returns_false(self):
        """Any other exception is caught and returns (False, None, msg)."""
        @safe_api_call
        def failing():
            raise ValueError("something broke")

        ok, result, err = failing()
        assert ok is False
        assert result is None
        assert err is not None
        assert "ValueError" in err
        assert "something broke" in err

    def test_unexpected_exception_message_format(self):
        """Unexpected exception message includes type name and message."""
        @safe_api_call
        def failing():
            raise KeyError("missing_key")

        ok, result, err = failing()
        assert "KeyError" in err
        assert "missing_key" in err


# ---------------------------------------------------------------------------
# TestGarminClientApiMethods
# ---------------------------------------------------------------------------

class TestGarminClientApiMethods:
    """Smoke tests for GarminClient API methods via safe_api_call + retry wrapping."""

    def _make_connected_client(self, test_garmin_config):
        """Return a GarminClient with a mocked inner Garmin client."""
        gc = GarminClient(test_garmin_config, rate_limit_delay=0.0)
        gc.client = MagicMock()
        gc._last_request_time = 0.0
        return gc

    # --- get_user_profile ---

    def test_get_user_profile_success(self, test_garmin_config):
        """get_user_profile returns (True, data, None) on success."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_full_name.return_value = "Jane Doe"

        ok, result, err = gc.get_user_profile()

        assert ok is True
        assert result == "Jane Doe"
        assert err is None

    def test_get_user_profile_error_propagated(self, test_garmin_config):
        """get_user_profile returns (False, None, msg) on GarthHTTPError."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_full_name.side_effect = _make_garth_http_error(403)

        ok, result, err = gc.get_user_profile()

        assert ok is False
        assert result is None
        assert "403" in err

    # --- get_user_summary ---

    def test_get_user_summary_success(self, test_garmin_config):
        """get_user_summary passes date string and returns wrapped result."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_user_summary.return_value = {"totalSteps": 9000}

        ok, result, err = gc.get_user_summary("2025-01-01")

        assert ok is True
        assert result == {"totalSteps": 9000}
        gc.client.get_user_summary.assert_called_once_with("2025-01-01")

    # --- get_heart_rates ---

    def test_get_heart_rates_success(self, test_garmin_config):
        """get_heart_rates returns wrapped heart rate data."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_heart_rates.return_value = {"heartRateValues": [[0, 60]]}

        ok, result, err = gc.get_heart_rates("2025-01-01")

        assert ok is True
        assert result["heartRateValues"] == [[0, 60]]

    # --- get_sleep_data ---

    def test_get_sleep_data_success(self, test_garmin_config):
        """get_sleep_data returns wrapped sleep data."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_sleep_data.return_value = {"dailySleepDTO": {"sleepTimeSeconds": 25200}}

        ok, result, err = gc.get_sleep_data("2025-01-01")

        assert ok is True
        assert "dailySleepDTO" in result

    # --- get_weigh_ins ---

    def test_get_weigh_ins_passes_iso_dates(self, test_garmin_config):
        """get_weigh_ins converts date objects to ISO strings before calling the API."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_weigh_ins.return_value = []

        start = date(2025, 1, 1)
        end = date(2025, 1, 31)
        ok, result, err = gc.get_weigh_ins(start, end)

        assert ok is True
        gc.client.get_weigh_ins.assert_called_once_with("2025-01-01", "2025-01-31")

    # --- get_activities_by_date ---

    def test_get_activities_by_date_with_activity_type(self, test_garmin_config):
        """get_activities_by_date forwards optional activity_type filter."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_activities_by_date.return_value = [{"activityId": 1}]

        ok, result, err = gc.get_activities_by_date(
            date(2025, 1, 1), date(2025, 1, 31), "running"
        )

        assert ok is True
        gc.client.get_activities_by_date.assert_called_once_with(
            "2025-01-01", "2025-01-31", "running"
        )

    # --- get_activity ---

    def test_get_activity_success(self, test_garmin_config):
        """get_activity returns detailed activity data."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_activity.return_value = {"activityId": 42, "activityName": "Trail Run"}

        ok, result, err = gc.get_activity(42)

        assert ok is True
        assert result["activityId"] == 42
        gc.client.get_activity.assert_called_once_with(42)

    # --- get_hydration_data ---

    def test_get_hydration_data_success(self, test_garmin_config):
        """get_hydration_data returns wrapped hydration data."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_hydration_data.return_value = {"totalIntakeInOz": 64.0}

        ok, result, err = gc.get_hydration_data("2025-01-01")

        assert ok is True
        assert result["totalIntakeInOz"] == 64.0

    # --- connection error on API method ---

    def test_api_method_connection_error(self, test_garmin_config):
        """A connection error during an API call is caught by safe_api_call."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_sleep_data.side_effect = GarminConnectConnectionError("timeout")

        ok, result, err = gc.get_sleep_data("2025-01-01")

        assert ok is False
        assert result is None
        assert "Connection error" in err or "connection" in err.lower()

    def test_api_method_too_many_requests(self, test_garmin_config):
        """A rate-limit error during an API call is caught by safe_api_call."""
        gc = self._make_connected_client(test_garmin_config)
        gc.client.get_hrv_data.side_effect = GarminConnectTooManyRequestsError("slow down")

        ok, result, err = gc.get_hrv_data("2025-01-01")

        assert ok is False
        assert result is None
        assert err is not None
