"""Tests for DailyHealthFetcher.fetch() method and related integration."""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, call

from src.fetchers.daily_health import DailyHealthFetcher


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

START_DATE = date(2025, 1, 10)
END_DATE = date(2025, 1, 10)
THREE_DAY_START = date(2025, 1, 10)
THREE_DAY_END = date(2025, 1, 12)


def _make_fetcher(mock_database, mock_garmin_client):
    """Create a DailyHealthFetcher with stubbed date-range and sync-state helpers."""
    fetcher = DailyHealthFetcher(
        db=mock_database,
        garmin_client=mock_garmin_client,
        user_id=1,
        category="daily_health",
    )
    # Pin date range to one day so tests are deterministic
    fetcher.determine_date_range = AsyncMock(return_value=(START_DATE, END_DATE))
    # Stub update_sync_state — we verify it separately
    fetcher.update_sync_state = AsyncMock()
    return fetcher


def _make_fetcher_3days(mock_database, mock_garmin_client):
    """Create a DailyHealthFetcher spanning three days."""
    fetcher = DailyHealthFetcher(
        db=mock_database,
        garmin_client=mock_garmin_client,
        user_id=1,
        category="daily_health",
    )
    fetcher.determine_date_range = AsyncMock(
        return_value=(THREE_DAY_START, THREE_DAY_END)
    )
    fetcher.update_sync_state = AsyncMock()
    return fetcher


def _good_garmin_client():
    """Return a MagicMock garmin client where every call succeeds."""
    client = MagicMock()
    client.get_user_summary = MagicMock(
        return_value=(True, {"totalSteps": 8000, "dailyStepGoal": 10000}, None)
    )
    client.get_heart_rates = MagicMock(
        return_value=(True, {"heartRateValues": [[1735689600000, 65]]}, None)
    )
    client.get_sleep_data = MagicMock(
        return_value=(
            True,
            {"dailySleepDTO": {"sleepTimeSeconds": 28800}, "sleepMovement": []},
            None,
        )
    )
    client.get_stress_data = MagicMock(
        return_value=(True, {"averageStressLevel": 25, "maxStressLevel": 50}, None)
    )
    client.get_body_battery = MagicMock(
        return_value=(
            True,
            {"charged": 40, "drained": 30, "highestValue": 95, "lowestValue": 40},
            None,
        )
    )
    return client


# ---------------------------------------------------------------------------
# Test: single-day success — all 5 data types stored
# ---------------------------------------------------------------------------


class TestFetchSingleDaySuccess:
    """fetch() processes one day and stores all 5 data types."""

    @pytest.mark.asyncio
    async def test_all_five_db_methods_called(self, mock_database, mock_garmin_client):
        """All five upsert methods are called for a successful single-day fetch."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        count, error = await fetcher.fetch()

        assert count == 1
        assert error is None
        mock_database.upsert_daily_summary.assert_called_once()
        mock_database.upsert_heart_rate_samples.assert_called_once()
        mock_database.upsert_sleep_data.assert_called_once()
        mock_database.upsert_stress_data.assert_called_once()
        mock_database.upsert_body_battery.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_correct_count_and_no_error(
        self, mock_database, mock_garmin_client
    ):
        """fetch() returns (1, None) when the single day succeeds."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        count, error = await fetcher.fetch()

        assert count == 1
        assert error is None


# ---------------------------------------------------------------------------
# Test: three-day success — records counted correctly
# ---------------------------------------------------------------------------


class TestFetchThreeDaysSuccess:
    """fetch() accumulates one record per day over a three-day range."""

    @pytest.mark.asyncio
    async def test_records_count_equals_days(self, mock_database, mock_garmin_client):
        """records_count equals number of days when all days succeed."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher_3days(mock_database, client)
        count, error = await fetcher.fetch()

        assert count == 3
        assert error is None

    @pytest.mark.asyncio
    async def test_upsert_called_once_per_day(self, mock_database, mock_garmin_client):
        """upsert_daily_summary is called exactly three times for a three-day range."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher_3days(mock_database, client)
        await fetcher.fetch()

        assert mock_database.upsert_daily_summary.call_count == 3


# ---------------------------------------------------------------------------
# Test: API failure on one type — others continue
# ---------------------------------------------------------------------------


class TestFetchPartialApiFailure:
    """When one non-summary API call fails the others still proceed."""

    @pytest.mark.asyncio
    async def test_heart_rate_failure_does_not_stop_others(
        self, mock_database, mock_garmin_client
    ):
        """Failing get_heart_rates does not prevent sleep/stress/body_battery storage."""
        client = _good_garmin_client()
        # Heart rate returns failure
        client.get_heart_rates = MagicMock(return_value=(False, None, "HR API error"))

        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=0)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        count, error = await fetcher.fetch()

        # Summary still stored
        mock_database.upsert_daily_summary.assert_called_once()
        # Heart rate NOT stored
        mock_database.upsert_heart_rate_samples.assert_not_called()
        # Sleep, stress, body battery still stored
        mock_database.upsert_sleep_data.assert_called_once()
        mock_database.upsert_stress_data.assert_called_once()
        mock_database.upsert_body_battery.assert_called_once()
        # No error in return value (non-summary failures are warnings, not errors)
        assert error is None

    @pytest.mark.asyncio
    async def test_stress_failure_does_not_stop_body_battery(
        self, mock_database, mock_garmin_client
    ):
        """Failing get_stress_data still allows body_battery to be stored."""
        client = _good_garmin_client()
        client.get_stress_data = MagicMock(
            return_value=(False, None, "Stress API error")
        )

        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        count, error = await fetcher.fetch()

        mock_database.upsert_stress_data.assert_not_called()
        mock_database.upsert_body_battery.assert_called_once()
        assert error is None


# ---------------------------------------------------------------------------
# Test: one day failing continues to next day
# ---------------------------------------------------------------------------


class TestFetchDayErrorContinues:
    """When get_user_summary raises an exception for a day, the next day proceeds."""

    @pytest.mark.asyncio
    async def test_exception_on_day1_still_processes_day2(
        self, mock_database, mock_garmin_client
    ):
        """An exception during _fetch_daily_summary is caught and next day runs."""
        client = _good_garmin_client()
        # First call raises, second and third calls succeed (three-day range)
        client.get_user_summary = MagicMock(
            side_effect=[
                Exception("Network error on day 1"),
                (True, {"totalSteps": 5000}, None),
                (True, {"totalSteps": 6000}, None),
            ]
        )

        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher_3days(mock_database, client)
        count, error = await fetcher.fetch()

        # Two days succeed, one fails
        assert count == 2
        # Error message recorded for the failing day
        assert error is not None
        assert "Network error on day 1" in error
        # upsert_daily_summary called only for the two successful days
        assert mock_database.upsert_daily_summary.call_count == 2

    @pytest.mark.asyncio
    async def test_error_messages_accumulated(
        self, mock_database, mock_garmin_client
    ):
        """All per-day errors are joined into the final error string."""
        client = _good_garmin_client()
        # All three days raise
        client.get_user_summary = MagicMock(
            side_effect=[
                Exception("Error day 1"),
                Exception("Error day 2"),
                Exception("Error day 3"),
            ]
        )

        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=0)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher_3days(mock_database, client)
        count, error = await fetcher.fetch()

        assert count == 0
        assert error is not None
        assert "Error day 1" in error
        assert "Error day 2" in error
        assert "Error day 3" in error


# ---------------------------------------------------------------------------
# Test: incremental mode uses last sync date
# ---------------------------------------------------------------------------


class TestFetchIncrementalMode:
    """fetch() in incremental mode delegates correctly to determine_date_range."""

    @pytest.mark.asyncio
    async def test_incremental_mode_passes_correct_args(
        self, mock_database, mock_garmin_client
    ):
        """In incremental mode determine_date_range is called with mode='incremental'."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = DailyHealthFetcher(
            db=mock_database,
            garmin_client=client,
            user_id=1,
            category="daily_health",
        )
        fetcher.determine_date_range = AsyncMock(return_value=(START_DATE, END_DATE))
        fetcher.update_sync_state = AsyncMock()

        await fetcher.fetch(mode="incremental", days_back=90)

        fetcher.determine_date_range.assert_called_once_with(
            "incremental", 90, None, None
        )

    @pytest.mark.asyncio
    async def test_incremental_uses_last_sync_date(
        self, mock_database, mock_garmin_client
    ):
        """Incremental sync starts from get_last_sync_date result."""
        last_sync = date(2025, 1, 5)
        mock_database.get_last_sync_date = AsyncMock(return_value=last_sync)
        mock_database.update_sync_state = AsyncMock()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        client = _good_garmin_client()

        fetcher = DailyHealthFetcher(
            db=mock_database,
            garmin_client=client,
            user_id=1,
            category="daily_health",
        )
        # Only stub update_sync_state, let determine_date_range run for real
        fetcher.update_sync_state = AsyncMock()

        start, _ = await fetcher.determine_date_range("incremental", 90)

        assert start == last_sync


# ---------------------------------------------------------------------------
# Test: full mode uses days_back
# ---------------------------------------------------------------------------


class TestFetchFullMode:
    """fetch() in full mode delegates correctly to determine_date_range."""

    @pytest.mark.asyncio
    async def test_full_mode_passes_correct_args(
        self, mock_database, mock_garmin_client
    ):
        """In full mode determine_date_range is called with mode='full'."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = DailyHealthFetcher(
            db=mock_database,
            garmin_client=client,
            user_id=1,
            category="daily_health",
        )
        fetcher.determine_date_range = AsyncMock(return_value=(START_DATE, END_DATE))
        fetcher.update_sync_state = AsyncMock()

        await fetcher.fetch(mode="full", days_back=30)

        fetcher.determine_date_range.assert_called_once_with("full", 30, None, None)

    @pytest.mark.asyncio
    async def test_full_mode_range_spans_days_back(
        self, mock_database, mock_garmin_client
    ):
        """Full sync date range spans exactly days_back days."""
        mock_database.get_last_sync_date = AsyncMock(return_value=None)
        mock_database.update_sync_state = AsyncMock()

        fetcher = DailyHealthFetcher(
            db=mock_database,
            garmin_client=mock_garmin_client,
            user_id=1,
            category="daily_health",
        )
        fetcher.update_sync_state = AsyncMock()

        start, end = await fetcher.determine_date_range("full", 30)

        # end is today+1 (to cover timezone differences); start is end - days_back
        assert (end - start).days == 30


# ---------------------------------------------------------------------------
# Test: explicit start/end dates
# ---------------------------------------------------------------------------


class TestFetchExplicitDates:
    """fetch() with explicit start_date and end_date."""

    @pytest.mark.asyncio
    async def test_explicit_dates_passed_to_determine_date_range(
        self, mock_database, mock_garmin_client
    ):
        """Explicit dates are forwarded verbatim to determine_date_range."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        explicit_start = date(2025, 3, 1)
        explicit_end = date(2025, 3, 5)

        fetcher = DailyHealthFetcher(
            db=mock_database,
            garmin_client=client,
            user_id=1,
            category="daily_health",
        )
        fetcher.determine_date_range = AsyncMock(
            return_value=(explicit_start, explicit_end)
        )
        fetcher.update_sync_state = AsyncMock()

        await fetcher.fetch(
            mode="incremental",
            days_back=90,
            start_date=explicit_start,
            end_date=explicit_end,
        )

        fetcher.determine_date_range.assert_called_once_with(
            "incremental", 90, explicit_start, explicit_end
        )

    @pytest.mark.asyncio
    async def test_explicit_dates_returned_unchanged_from_determine_date_range(
        self, mock_database, mock_garmin_client
    ):
        """determine_date_range returns explicit dates unchanged."""
        mock_database.get_last_sync_date = AsyncMock(return_value=None)

        explicit_start = date(2025, 3, 1)
        explicit_end = date(2025, 3, 5)

        fetcher = DailyHealthFetcher(
            db=mock_database,
            garmin_client=mock_garmin_client,
            user_id=1,
            category="daily_health",
        )

        start, end = await fetcher.determine_date_range(
            "incremental", 90, explicit_start, explicit_end
        )

        assert start == explicit_start
        assert end == explicit_end


# ---------------------------------------------------------------------------
# Test: all API calls returning success=False
# ---------------------------------------------------------------------------


class TestFetchAllApiCallsFail:
    """When every API call returns success=False the fetcher returns an error."""

    @pytest.mark.asyncio
    async def test_all_summary_failures_produce_error(
        self, mock_database, mock_garmin_client
    ):
        """When get_user_summary fails for every day the error string is non-empty."""
        client = MagicMock()
        # summary raises so it counts as an error per day
        client.get_user_summary = MagicMock(
            side_effect=Exception("API unavailable")
        )
        client.get_heart_rates = MagicMock(return_value=(False, None, "err"))
        client.get_sleep_data = MagicMock(return_value=(False, None, "err"))
        client.get_stress_data = MagicMock(return_value=(False, None, "err"))
        client.get_body_battery = MagicMock(return_value=(False, None, "err"))

        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=0)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        count, error = await fetcher.fetch()

        assert count == 0
        assert error is not None
        assert len(error) > 0

    @pytest.mark.asyncio
    async def test_no_db_writes_when_all_apis_fail(
        self, mock_database, mock_garmin_client
    ):
        """No upsert calls happen when every API returns success=False."""
        client = MagicMock()
        client.get_user_summary = MagicMock(return_value=(False, None, "err"))
        client.get_heart_rates = MagicMock(return_value=(False, None, "err"))
        client.get_sleep_data = MagicMock(return_value=(False, None, "err"))
        client.get_stress_data = MagicMock(return_value=(False, None, "err"))
        client.get_body_battery = MagicMock(return_value=(False, None, "err"))

        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=0)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        await fetcher.fetch()

        # success=False short-circuits before calling DB
        mock_database.upsert_daily_summary.assert_not_called()
        mock_database.upsert_heart_rate_samples.assert_not_called()
        mock_database.upsert_sleep_data.assert_not_called()
        mock_database.upsert_stress_data.assert_not_called()
        mock_database.upsert_body_battery.assert_not_called()


# ---------------------------------------------------------------------------
# Test: update_sync_state called with correct arguments
# ---------------------------------------------------------------------------


class TestFetchCallsUpdateSyncState:
    """fetch() must call update_sync_state with the end date and final count."""

    @pytest.mark.asyncio
    async def test_update_sync_state_called_with_end_date_and_count(
        self, mock_database, mock_garmin_client
    ):
        """update_sync_state receives the range end date and the records_count."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        count, error = await fetcher.fetch()

        fetcher.update_sync_state.assert_called_once_with(END_DATE, count, None)

    @pytest.mark.asyncio
    async def test_update_sync_state_receives_error_string_on_partial_failure(
        self, mock_database, mock_garmin_client
    ):
        """update_sync_state receives a non-None error when daily summary fails."""
        client = _good_garmin_client()
        client.get_user_summary = MagicMock(
            side_effect=Exception("oops")
        )

        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=0)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher(mock_database, client)
        count, error = await fetcher.fetch()

        # update_sync_state should be called with the error
        args = fetcher.update_sync_state.call_args
        assert args[0][2] is not None  # error_message positional arg
        assert "oops" in args[0][2]

    @pytest.mark.asyncio
    async def test_update_sync_state_called_exactly_once(
        self, mock_database, mock_garmin_client
    ):
        """update_sync_state is called exactly once regardless of day count."""
        client = _good_garmin_client()
        mock_database.upsert_daily_summary = AsyncMock()
        mock_database.upsert_heart_rate_samples = AsyncMock(return_value=1)
        mock_database.upsert_sleep_data = AsyncMock()
        mock_database.upsert_stress_data = AsyncMock()
        mock_database.upsert_body_battery = AsyncMock()

        fetcher = _make_fetcher_3days(mock_database, client)
        await fetcher.fetch()

        fetcher.update_sync_state.assert_called_once()
