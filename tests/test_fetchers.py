"""Tests for data fetchers and transformations."""

import pytest
import json
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.fetchers.base import BaseFetcher
from src.fetchers.daily_health import DailyHealthFetcher


class TestBaseFetcherTimestampParsing:
    """Tests for BaseFetcher timestamp parsing."""

    def test_parse_timestamp_milliseconds(self):
        """Test parsing timestamp from milliseconds epoch."""
        ms = 1735689600000  # 2025-01-01 00:00:00 UTC
        result = BaseFetcher._parse_timestamp(ms)
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_parse_timestamp_seconds(self):
        """Test parsing timestamp from seconds epoch."""
        seconds = 1735689600
        result = BaseFetcher._parse_timestamp(seconds)
        assert isinstance(result, datetime)

    def test_parse_timestamp_iso_string(self):
        """Test parsing ISO 8601 timestamp string."""
        iso_str = "2025-01-01T12:30:00Z"
        result = BaseFetcher._parse_timestamp(iso_str)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_parse_timestamp_iso_string_with_offset(self):
        """Test parsing ISO 8601 with timezone offset."""
        iso_str = "2025-01-01T12:30:00+00:00"
        result = BaseFetcher._parse_timestamp(iso_str)
        assert isinstance(result, datetime)

    def test_parse_timestamp_date_string(self):
        """Test parsing date string (YYYY-MM-DD)."""
        date_str = "2025-01-01"
        result = BaseFetcher._parse_timestamp(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_parse_timestamp_none(self):
        """Test parsing None returns None."""
        result = BaseFetcher._parse_timestamp(None)
        assert result is None

    def test_parse_timestamp_empty_string(self):
        """Test parsing empty string returns None."""
        result = BaseFetcher._parse_timestamp("")
        assert result is None

    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp returns None."""
        result = BaseFetcher._parse_timestamp("not a timestamp")
        assert result is None


class TestBaseFetcherEnsureDict:
    """Tests for BaseFetcher._ensure_dict method."""

    def test_ensure_dict_with_dict(self):
        """Test _ensure_dict with dict input."""
        data = {"key": "value"}
        result = BaseFetcher._ensure_dict(data)
        assert result == data

    def test_ensure_dict_with_list_of_dicts(self):
        """Test _ensure_dict with list of dicts."""
        data = [{"key": "value"}]
        result = BaseFetcher._ensure_dict(data)
        assert result == {"key": "value"}

    def test_ensure_dict_with_empty_list(self):
        """Test _ensure_dict with empty list returns None."""
        result = BaseFetcher._ensure_dict([])
        assert result is None

    def test_ensure_dict_with_none(self):
        """Test _ensure_dict with None returns None."""
        result = BaseFetcher._ensure_dict(None)
        assert result is None

    def test_ensure_dict_with_non_dict_list(self):
        """Test _ensure_dict with list of non-dicts returns None."""
        result = BaseFetcher._ensure_dict(["string"])
        assert result is None


class TestDailyHealthFetcherTransformations:
    """Tests for DailyHealthFetcher data transformations."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        """Create a DailyHealthFetcher instance for testing."""
        return DailyHealthFetcher(
            db=mock_database,
            garmin_client=mock_garmin_client,
            user_id=1,
            category="daily_health",
        )

    def test_transform_daily_summary(self, fetcher):
        """Test daily summary data transformation."""
        test_date = date(2025, 1, 1)
        raw_data = {
            "totalSteps": 10000,
            "dailyStepGoal": 12000,
            "totalDistanceMeters": 8500.0,
            "activeKilocalories": 400,
            "bmrKilocalories": 1600,
            "totalKilocalories": 2000,
            "maxHeartRate": 150,
            "minHeartRate": 50,
            "restingHeartRate": 55,
            "averageHeartRate": 85,
            "averageStressLevel": 30,
            "maxStressLevel": 60,
            "stressQualifier": "low_stress",
        }

        result = fetcher._transform_daily_summary(test_date, raw_data)

        assert result["calendar_date"] == test_date
        assert result["total_steps"] == 10000
        assert result["step_goal"] == 12000
        assert result["total_distance_meters"] == 8500.0
        assert result["max_heart_rate"] == 150

    def test_transform_heart_rate_samples(self, fetcher):
        """Test heart rate samples transformation."""
        raw_data = {
            "heartRateValues": [
                {"timestamp": 1735689600000, "heartRate": 75},
                {"timestamp": 1735689660000, "heartRate": 78},
                {"timestamp": 1735689720000, "heartRate": 80},
            ]
        }

        result = fetcher._transform_heart_rate_samples(raw_data)

        assert len(result) == 3
        assert result[0]["heart_rate"] == 75
        assert result[1]["heart_rate"] == 78
        assert isinstance(result[0]["timestamp"], datetime)

    def test_transform_heart_rate_samples_empty(self, fetcher):
        """Test heart rate samples with no data."""
        raw_data = {"heartRateValues": []}
        result = fetcher._transform_heart_rate_samples(raw_data)
        assert result == []

    def test_transform_heart_rate_samples_no_key(self, fetcher):
        """Test heart rate samples when key is missing."""
        raw_data = {}
        result = fetcher._transform_heart_rate_samples(raw_data)
        assert result == []

    def test_transform_heart_rate_samples_list_format(self, fetcher):
        """Test heart rate samples in list format."""
        raw_data = {
            "heartRateValues": [
                [1735689600000, 75],
                [1735689660000, 78],
            ]
        }

        result = fetcher._transform_heart_rate_samples(raw_data)

        assert len(result) == 2
        assert result[0]["heart_rate"] == 75

    def test_transform_sleep_data(self, fetcher):
        """Test sleep data transformation."""
        test_date = date(2025, 1, 1)
        raw_data = {
            "dailySleepDTO": {
                "sleepStartTimestampGMT": 1735689600000,
                "sleepEndTimestampGMT": 1735724400000,
                "sleepTimeSeconds": 36000,
                "deepSleepSeconds": 10000,
                "lightSleepSeconds": 20000,
                "remSleepSeconds": 6000,
                "awakeSleepSeconds": 3600,
                "sleepScores": {
                    "overall": {
                        "value": 85,
                        "qualifierKey": "good_sleep",
                    }
                },
            },
            "sleepMovement": [],
        }

        result = fetcher._transform_sleep_data(test_date, raw_data)

        assert result["calendar_date"] == test_date
        assert result["total_sleep_seconds"] == 36000
        assert result["deep_sleep_seconds"] == 10000
        assert result["sleep_score"] == 85

    def test_transform_stress_data(self, fetcher):
        """Test stress data transformation."""
        test_date = date(2025, 1, 1)
        raw_data = {
            "averageStressLevel": 35,
            "maxStressLevel": 60,
            "restStressDuration": 1800,
            "activityStressDuration": 3600,
            "lowStressDuration": 14400,
            "mediumStressDuration": 7200,
            "highStressDuration": 3600,
        }

        result = fetcher._transform_stress_data(test_date, raw_data)

        assert result["calendar_date"] == test_date
        assert result["average_stress_level"] == 35
        assert result["max_stress_level"] == 60

    def test_transform_body_battery_data(self, fetcher):
        """Test body battery data transformation."""
        test_date = date(2025, 1, 1)
        raw_data = {
            "startTimestampGMT": 1735689600000,
            "endTimestampGMT": 1735776000000,
            "charged": 30,
            "drained": 25,
            "highestValue": 100,
            "lowestValue": 45,
            "bodyBatteryValuesArray": [],
        }

        result = fetcher._transform_body_battery_data(test_date, raw_data)

        assert result["calendar_date"] == test_date
        assert result["charged_value"] == 30
        assert result["drained_value"] == 25
        assert result["highest_value"] == 100


class TestDailyHealthFetcherDateRange:
    """Tests for DailyHealthFetcher date range determination."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        """Create a DailyHealthFetcher instance for testing."""
        return DailyHealthFetcher(
            db=mock_database,
            garmin_client=mock_garmin_client,
            user_id=1,
            category="daily_health",
        )

    @pytest.mark.asyncio
    async def test_determine_date_range_explicit_dates(self, fetcher):
        """Test date range with explicit start/end dates."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 10)

        result_start, result_end = await fetcher.determine_date_range(
            "incremental", 90, start, end
        )

        assert result_start == start
        assert result_end == end

    @pytest.mark.asyncio
    async def test_determine_date_range_incremental_no_previous(self, fetcher):
        """Test incremental mode with no previous sync."""
        # Mock get_last_sync_date to return None
        fetcher.db.get_last_sync_date = AsyncMock(return_value=None)

        result_start, result_end = await fetcher.determine_date_range(
            "incremental", 90
        )

        # Should fall back to 90 days back
        assert result_start < result_end
        assert (result_end - result_start).days == 90

    @pytest.mark.asyncio
    async def test_determine_date_range_incremental_with_previous(self, fetcher):
        """Test incremental mode with previous sync date."""
        previous_sync = date(2025, 1, 1)
        fetcher.db.get_last_sync_date = AsyncMock(return_value=previous_sync)

        result_start, result_end = await fetcher.determine_date_range(
            "incremental", 90
        )

        assert result_start == previous_sync

    @pytest.mark.asyncio
    async def test_determine_date_range_full_mode(self, fetcher):
        """Test full sync mode."""
        fetcher.db.get_last_sync_date = AsyncMock(return_value=None)

        result_start, result_end = await fetcher.determine_date_range(
            "full", 30
        )

        # Should be 30 days back
        assert (result_end - result_start).days == 30

    @pytest.mark.asyncio
    async def test_determine_date_range_start_after_end(self, fetcher):
        """Test that start date is never after end date."""
        fetcher.db.get_last_sync_date = AsyncMock(return_value=None)

        result_start, result_end = await fetcher.determine_date_range(
            "full", 0  # 0 days back means start == end initially, but clamped
        )

        assert result_start <= result_end
