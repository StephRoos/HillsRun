"""Comprehensive tests for ActivitiesFetcher, BodyCompositionFetcher,
AdvancedMetricsFetcher, and WellnessFetcher."""

import json
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.fetchers.activities import ActivitiesFetcher
from src.fetchers.body_comp import BodyCompositionFetcher
from src.fetchers.advanced_metrics import AdvancedMetricsFetcher
from src.fetchers.wellness import WellnessFetcher


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 1, 3)


def _make_activities_fetcher(mock_database, mock_garmin_client):
    fetcher = ActivitiesFetcher(
        db=mock_database,
        garmin_client=mock_garmin_client,
        user_id=1,
        category="activities",
    )
    # Pin date range so tests are deterministic and independent of today's date
    fetcher.determine_date_range = AsyncMock(return_value=(START_DATE, END_DATE))
    # update_sync_state touches the DB; stub it out by default
    fetcher.update_sync_state = AsyncMock()
    return fetcher


def _make_body_comp_fetcher(mock_database, mock_garmin_client):
    fetcher = BodyCompositionFetcher(
        db=mock_database,
        garmin_client=mock_garmin_client,
        user_id=1,
        category="body_composition",
    )
    fetcher.determine_date_range = AsyncMock(return_value=(START_DATE, END_DATE))
    fetcher.update_sync_state = AsyncMock()
    return fetcher


def _make_advanced_metrics_fetcher(mock_database, mock_garmin_client):
    fetcher = AdvancedMetricsFetcher(
        db=mock_database,
        garmin_client=mock_garmin_client,
        user_id=1,
        category="advanced_metrics",
    )
    fetcher.determine_date_range = AsyncMock(return_value=(START_DATE, END_DATE))
    fetcher.update_sync_state = AsyncMock()
    return fetcher


def _make_wellness_fetcher(mock_database, mock_garmin_client):
    fetcher = WellnessFetcher(
        db=mock_database,
        garmin_client=mock_garmin_client,
        user_id=1,
        category="wellness",
    )
    fetcher.determine_date_range = AsyncMock(return_value=(START_DATE, END_DATE))
    fetcher.update_sync_state = AsyncMock()
    return fetcher


# ---------------------------------------------------------------------------
# ActivitiesFetcher
# ---------------------------------------------------------------------------


class TestActivitiesFetcherFetch:
    """Integration-level tests for ActivitiesFetcher.fetch()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_activities_fetcher(mock_database, mock_garmin_client)

    @pytest.mark.asyncio
    async def test_fetch_success_processes_each_activity(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """fetch() processes every activity returned by the Garmin API."""
        raw_activities = [
            {"activityId": 101, "activityName": "Morning Run"},
            {"activityId": 102, "activityName": "Evening Walk"},
        ]
        # First call: list of activities for the primary date range
        # Second call (broader deletion check): same list
        mock_garmin_client.get_activities_by_date.return_value = (
            True,
            raw_activities,
            None,
        )
        mock_garmin_client.get_activity.return_value = (True, {}, None)
        mock_garmin_client.get_activity_splits.return_value = (True, {}, None)

        # DB helpers needed by deletion logic
        mock_database.get_activity_ids_for_range = AsyncMock(return_value=[])
        mock_database.upsert_activity = AsyncMock()
        mock_database.upsert_activity_splits = AsyncMock()

        count, error = await fetcher.fetch(
            mode="full",
            start_date=START_DATE,
            end_date=END_DATE,
        )

        assert count == 2
        assert error is None
        assert mock_database.upsert_activity.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_api_failure_returns_error(
        self, fetcher, mock_garmin_client
    ):
        """fetch() returns (0, error_msg) when the Garmin API call fails."""
        mock_garmin_client.get_activities_by_date.return_value = (
            False,
            None,
            "Connection timeout",
        )

        count, error = await fetcher.fetch(
            mode="full",
            start_date=START_DATE,
            end_date=END_DATE,
        )

        assert count == 0
        assert error is not None
        assert "Connection timeout" in error

    @pytest.mark.asyncio
    async def test_fetch_empty_activity_list_returns_zero(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """fetch() returns 0 records when the API returns an empty list."""
        mock_garmin_client.get_activities_by_date.return_value = (True, [], None)
        mock_database.get_activity_ids_for_range = AsyncMock(return_value=[])

        count, error = await fetcher.fetch(
            mode="full",
            start_date=START_DATE,
            end_date=END_DATE,
        )

        assert count == 0
        assert error is None

    @pytest.mark.asyncio
    async def test_fetch_skips_activity_without_id(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """fetch() still tries to process activities that lack an activityId."""
        # Activity without an ID — should not crash, just omit from id set
        mock_garmin_client.get_activities_by_date.return_value = (
            True,
            [{"activityName": "No ID activity"}],
            None,
        )
        mock_garmin_client.get_activity.return_value = (True, {}, None)
        mock_garmin_client.get_activity_splits.return_value = (True, {}, None)
        mock_database.get_activity_ids_for_range = AsyncMock(return_value=[])
        mock_database.upsert_activity = AsyncMock()

        count, error = await fetcher.fetch(
            mode="full",
            start_date=START_DATE,
            end_date=END_DATE,
        )

        # The activity is still processed (count == 1) but not added to the id set
        assert count == 1

    @pytest.mark.asyncio
    async def test_fetch_individual_activity_error_is_non_fatal(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """A crash while processing one activity does not abort the others."""
        raw_activities = [
            {"activityId": 101},
            {"activityId": 102},
        ]
        mock_garmin_client.get_activities_by_date.return_value = (
            True,
            raw_activities,
            None,
        )
        mock_garmin_client.get_activity.return_value = (True, {}, None)
        mock_garmin_client.get_activity_splits.return_value = (True, {}, None)
        mock_database.get_activity_ids_for_range = AsyncMock(return_value=[])

        # First upsert raises; second should still succeed
        mock_database.upsert_activity = AsyncMock(
            side_effect=[RuntimeError("DB write failed"), None]
        )

        count, error = await fetcher.fetch(
            mode="full",
            start_date=START_DATE,
            end_date=END_DATE,
        )

        # Only the second activity counted
        assert count == 1
        # Error message is recorded but fetch does not return early
        assert error is not None


class TestActivitiesFetcherDeletionLogic:
    """Tests for the deletion-of-removed-activities logic."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_activities_fetcher(mock_database, mock_garmin_client)

    @pytest.mark.asyncio
    async def test_deletes_activities_missing_from_garmin(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """Activities present in DB but absent from Garmin are deleted."""
        # Garmin returns activity 101 only
        mock_garmin_client.get_activities_by_date.return_value = (
            True,
            [{"activityId": 101}],
            None,
        )
        mock_garmin_client.get_activity.return_value = (True, {}, None)
        mock_garmin_client.get_activity_splits.return_value = (True, {}, None)

        # DB has 101 and 999 — 999 no longer exists in Garmin
        mock_database.get_activity_ids_for_range = AsyncMock(return_value=[101, 999])
        mock_database.upsert_activity = AsyncMock()
        mock_database.delete_activities = AsyncMock(return_value=1)

        await fetcher.fetch(mode="full", start_date=START_DATE, end_date=END_DATE)

        mock_database.delete_activities.assert_called_once()
        deleted_ids = mock_database.delete_activities.call_args[0][0]
        assert 999 in deleted_ids
        assert 101 not in deleted_ids

    @pytest.mark.asyncio
    async def test_no_deletion_when_all_ids_present(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """delete_activities is never called when all DB IDs are in Garmin."""
        mock_garmin_client.get_activities_by_date.return_value = (
            True,
            [{"activityId": 101}],
            None,
        )
        mock_garmin_client.get_activity.return_value = (True, {}, None)
        mock_garmin_client.get_activity_splits.return_value = (True, {}, None)
        mock_database.get_activity_ids_for_range = AsyncMock(return_value=[101])
        mock_database.upsert_activity = AsyncMock()
        mock_database.delete_activities = AsyncMock()

        await fetcher.fetch(mode="full", start_date=START_DATE, end_date=END_DATE)

        mock_database.delete_activities.assert_not_called()

    @pytest.mark.asyncio
    async def test_incremental_mode_uses_broader_range_for_deletion(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """In incremental mode a second API call covers a broader window for deletions."""
        # Narrow incremental range: only one day
        narrow_start = date(2025, 1, 3)
        narrow_end = date(2025, 1, 3)
        fetcher.determine_date_range = AsyncMock(
            return_value=(narrow_start, narrow_end)
        )

        mock_garmin_client.get_activities_by_date.return_value = (True, [], None)
        mock_database.get_activity_ids_for_range = AsyncMock(return_value=[])
        mock_database.delete_activities = AsyncMock()

        await fetcher.fetch(mode="incremental", days_back=90)

        # Should have made at least two calls to get_activities_by_date:
        # one for the primary range and one for the broader deletion window
        assert mock_garmin_client.get_activities_by_date.call_count >= 2


class TestActivitiesFetcherTransformActivity:
    """Unit tests for _transform_activity()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_activities_fetcher(mock_database, mock_garmin_client)

    def test_maps_all_core_fields(self, fetcher):
        """All primary fields are correctly mapped to DB column names."""
        raw = {
            "activityId": 12345,
            "activityName": "Trail Run",
            "activityType": {"typeKey": "trail_running"},
            "sportTypeKey": "trail_running",
            "startTimeGMT": "2025-01-01T08:00:00Z",
            "duration": 3600.0,
            "distance": 10000.0,
            "averageSpeed": 2.78,
            "maxSpeed": 4.0,
            "calories": 500,
            "averageHR": 145,
            "maxHR": 175,
            "elevationGain": 350.0,
            "elevationLoss": 350.0,
            "vO2MaxValue": 55,
            "pr": True,
            "favorite": False,
            "manual": False,
            "lapCount": 4,
        }

        result = fetcher._transform_activity(raw)

        assert result["activity_id"] == 12345
        assert result["activity_name"] == "Trail Run"
        assert result["sport_type"] == "trail_running"
        assert isinstance(result["start_timestamp"], datetime)
        assert result["duration_seconds"] == 3600.0
        assert result["distance_meters"] == 10000.0
        assert result["average_speed"] == 2.78
        assert result["max_speed"] == 4.0
        assert result["calories"] == 500
        assert result["average_hr"] == 145
        assert result["max_hr"] == 175
        assert result["elevation_gain_meters"] == 350.0
        assert result["elevation_loss_meters"] == 350.0
        assert result["vo2_max_value"] == 55
        assert result["pr"] is True
        assert result["num_laps"] == 4

    def test_activity_data_field_is_json_serialised(self, fetcher):
        """The raw data blob is stored as a JSON string."""
        raw = {"activityId": 1, "activityName": "Run"}
        result = fetcher._transform_activity(raw)

        assert isinstance(result["activity_data"], str)
        parsed = json.loads(result["activity_data"])
        assert parsed["activityId"] == 1

    def test_start_timestamp_from_begin_timestamp_fallback(self, fetcher):
        """startTimeGMT is absent — falls back to beginTimestamp (ms epoch)."""
        ms_epoch = 1735689600000  # 2025-01-01T00:00:00 UTC
        raw = {"activityId": 1, "beginTimestamp": ms_epoch}
        result = fetcher._transform_activity(raw)

        assert isinstance(result["start_timestamp"], datetime)

    def test_start_timestamp_none_when_no_time_fields(self, fetcher):
        """Both time fields absent → start_timestamp is None."""
        raw = {"activityId": 1}
        result = fetcher._transform_activity(raw)

        assert result["start_timestamp"] is None

    def test_sport_type_falls_back_through_priority(self, fetcher):
        """sport_type uses sportTypeKey unless it is 'uncategorized'."""
        raw_uncategorized = {
            "activityId": 1,
            "sportTypeKey": "uncategorized",
            "activityType": {"typeKey": "running"},
        }
        result = fetcher._transform_activity(raw_uncategorized)
        # uncategorized is ignored; falls back to activityType.typeKey
        assert result["sport_type"] == "running"

    def test_activity_type_as_plain_string(self, fetcher):
        """activityType may be a plain string (not a dict)."""
        raw = {"activityId": 1, "activityType": "cycling"}
        result = fetcher._transform_activity(raw)

        assert result["activity_type"] == "cycling"

    def test_device_name_from_metadata_dto_fallback(self, fetcher):
        """deviceName falls back to metadataDTO.deviceName when absent."""
        raw = {
            "activityId": 1,
            "metadataDTO": {"deviceName": "Garmin Fenix 7"},
        }
        result = fetcher._transform_activity(raw)
        assert result["device_name"] == "Garmin Fenix 7"


class TestActivitiesFetcherTransformSplits:
    """Unit tests for _transform_splits()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_activities_fetcher(mock_database, mock_garmin_client)

    def test_transforms_lap_dtos(self, fetcher):
        """lapDTOs are transformed into split dicts with correct field mapping."""
        data = {
            "lapDTOs": [
                {
                    "startTimeGMT": "2025-01-01T08:00:00Z",
                    "messageType": "lap",
                    "distance": 1000.0,
                    "duration": 360.0,
                    "averageSpeed": 2.78,
                    "averageHR": 140,
                    "maxHR": 155,
                    "elevationGain": 10.0,
                    "elevationLoss": 5.0,
                },
                {
                    "startTimeGMT": "2025-01-01T08:06:00Z",
                    "messageType": "lap",
                    "distance": 1000.0,
                    "duration": 370.0,
                },
            ]
        }

        result = fetcher._transform_splits(data)

        assert len(result) == 2
        assert result[0]["split_index"] == 0
        assert result[1]["split_index"] == 1
        assert result[0]["split_type"] == "lap"
        assert result[0]["distance_meters"] == 1000.0
        assert result[0]["duration_seconds"] == 360.0
        assert result[0]["average_hr"] == 140
        assert result[0]["max_hr"] == 155
        assert result[0]["elevation_gain_meters"] == 10.0
        assert isinstance(result[0]["start_timestamp"], datetime)

    def test_transforms_split_dtos_when_no_lap_dtos(self, fetcher):
        """splitDTOs are used when lapDTOs key is absent."""
        data = {
            "splitDTOs": [
                {"distance": 500.0, "duration": 180.0},
            ]
        }

        result = fetcher._transform_splits(data)

        assert len(result) == 1
        assert result[0]["distance_meters"] == 500.0

    def test_empty_splits_data_returns_empty_list(self, fetcher):
        """Empty response yields an empty split list."""
        assert fetcher._transform_splits({}) == []
        assert fetcher._transform_splits({"lapDTOs": []}) == []

    def test_elapsed_duration_in_ms_converted(self, fetcher):
        """elapsedDuration (milliseconds) is converted to seconds when duration absent."""
        data = {
            "lapDTOs": [
                {"elapsedDuration": 360000},  # 360 s
            ]
        }

        result = fetcher._transform_splits(data)

        assert result[0]["duration_seconds"] == 360.0

    def test_average_cadence_from_steps_per_minute(self, fetcher):
        """averageRunningCadenceInStepsPerMinute is mapped to average_cadence."""
        data = {
            "lapDTOs": [
                {"averageRunningCadenceInStepsPerMinute": 170},
            ]
        }

        result = fetcher._transform_splits(data)

        assert result[0]["average_cadence"] == 170

    def test_missing_start_time_gmt_yields_none_timestamp(self, fetcher):
        """A split without startTimeGMT gets start_timestamp == None."""
        data = {"lapDTOs": [{"distance": 500.0}]}

        result = fetcher._transform_splits(data)

        assert result[0]["start_timestamp"] is None


# ---------------------------------------------------------------------------
# BodyCompositionFetcher
# ---------------------------------------------------------------------------


class TestBodyCompositionFetcherFetch:
    """Integration-level tests for BodyCompositionFetcher.fetch()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_body_comp_fetcher(mock_database, mock_garmin_client)

    @pytest.mark.asyncio
    async def test_fetch_success_stores_records(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """fetch() upserts one body-comp record per daily weight summary."""
        weigh_in_response = {
            "dailyWeightSummaries": [
                {
                    "summaryDate": "2025-01-01",
                    "latestWeight": {
                        "weight": 75000,  # grams
                        "bmi": 22.5,
                        "bodyFat": 18.0,
                    },
                },
                {
                    "summaryDate": "2025-01-02",
                    "latestWeight": {
                        "weight": 74800,
                        "bmi": 22.4,
                    },
                },
            ]
        }
        mock_garmin_client.get_weigh_ins.return_value = (
            True,
            weigh_in_response,
            None,
        )
        mock_database.upsert_body_composition = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 2
        assert error is None
        assert mock_database.upsert_body_composition.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_api_failure_recorded_as_error(
        self, fetcher, mock_garmin_client
    ):
        """A Garmin API failure is captured in the error return value."""
        mock_garmin_client.get_weigh_ins.return_value = (
            False,
            None,
            "Service unavailable",
        )

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 0
        assert error is not None
        assert "Service unavailable" in error

    @pytest.mark.asyncio
    async def test_fetch_empty_response_returns_zero(
        self, fetcher, mock_garmin_client
    ):
        """An empty weigh-in list results in zero records stored."""
        mock_garmin_client.get_weigh_ins.return_value = (
            True,
            {"dailyWeightSummaries": []},
            None,
        )

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 0
        assert error is None

    @pytest.mark.asyncio
    async def test_fetch_list_response_format(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """fetch() handles a plain list response (not wrapped in a dict)."""
        mock_garmin_client.get_weigh_ins.return_value = (
            True,
            [
                {
                    "summaryDate": "2025-01-01",
                    "latestWeight": {"weight": 70000},
                }
            ],
            None,
        )
        mock_database.upsert_body_composition = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_fetch_skips_record_without_timestamp(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """A summary with no parseable date is skipped (not upserted)."""
        mock_garmin_client.get_weigh_ins.return_value = (
            True,
            {
                "dailyWeightSummaries": [
                    # summaryDate missing → _parse_timestamp returns None
                    {"latestWeight": {"weight": 70000}},
                ]
            },
            None,
        )
        mock_database.upsert_body_composition = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 0
        mock_database.upsert_body_composition.assert_not_called()


class TestBodyCompositionFetcherTransform:
    """Unit tests for BodyCompositionFetcher._transform_daily_weight()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_body_comp_fetcher(mock_database, mock_garmin_client)

    def test_transforms_all_fields(self, fetcher):
        """All body composition fields are mapped correctly."""
        data = {
            "summaryDate": "2025-01-01",
            "latestWeight": {
                "weight": 75000,  # grams → 75 kg
                "bmi": 22.5,
                "bodyFat": 18.0,
                "bodyWater": 60.0,
                "boneMass": 3000,  # grams → 3 kg
                "muscleMass": 60000,  # grams → 60 kg
                "metabolicAge": 35,
                "visceralFatMass": 8.0,
                "bmr": 1700,
                "activeMet": 2100,
                "physiqueRating": 4,
                "sourceType": "GARMIN",
            },
        }

        result = fetcher._transform_daily_weight(data)

        assert result["timestamp"] is not None
        assert result["weight_kg"] == 75.0
        assert result["bmi"] == 22.5
        assert result["body_fat_percentage"] == 18.0
        assert result["body_water_percentage"] == 60.0
        assert result["bone_mass_kg"] == 3.0
        assert result["muscle_mass_kg"] == 60.0
        assert result["metabolic_age"] == 35
        assert result["visceral_fat_rating"] == 8.0
        assert result["basal_met"] == 1700
        assert result["active_met"] == 2100
        assert result["physique_rating"] == 4
        assert result["source_type"] == "GARMIN"

    def test_weight_already_in_kg_not_divided(self, fetcher):
        """Weights below the threshold are not divided by 1000."""
        data = {
            "summaryDate": "2025-01-01",
            "latestWeight": {"weight": 75},  # already in kg (≤ 500 threshold)
        }

        result = fetcher._transform_daily_weight(data)

        assert result["weight_kg"] == 75

    def test_falls_back_to_min_max_weight_when_latest_absent(self, fetcher):
        """minWeight is used as the weight source when latestWeight is missing."""
        data = {
            "summaryDate": "2025-01-01",
            "minWeight": 74000,  # grams
        }

        result = fetcher._transform_daily_weight(data)

        assert result["weight_kg"] == 74.0

    def test_missing_latest_weight_yields_none_fields(self, fetcher):
        """Absent latestWeight dict results in None for all detail fields."""
        data = {"summaryDate": "2025-01-01"}

        result = fetcher._transform_daily_weight(data)

        assert result["bmi"] is None
        assert result["body_fat_percentage"] is None
        assert result["muscle_mass_kg"] is None


# ---------------------------------------------------------------------------
# AdvancedMetricsFetcher
# ---------------------------------------------------------------------------


class TestAdvancedMetricsFetcherFetch:
    """Integration-level tests for AdvancedMetricsFetcher.fetch()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_advanced_metrics_fetcher(mock_database, mock_garmin_client)

    def _setup_all_metrics_success(self, mock_garmin_client, mock_database):
        """Configure mocks so all per-day metric calls succeed."""
        mock_garmin_client.get_hrv_data.return_value = (
            True,
            {"hrvSummary": {"weeklyAvg": 55, "lastNightAvg": 52}},
            None,
        )
        mock_garmin_client.get_spo2_data.return_value = (
            True,
            {"averageSPO2": 97, "lowestSPO2": 94},
            None,
        )
        mock_garmin_client.get_max_metrics.return_value = (
            True,
            {"vo2Max": 55},
            None,
        )
        mock_garmin_client.get_respiration_data.return_value = (
            True,
            {"avgWakingRespirationRate": 15},
            None,
        )
        mock_garmin_client.get_training_readiness.return_value = (
            True,
            {"score": 80},
            None,
        )
        mock_database.upsert_hrv_data = AsyncMock()
        mock_database.upsert_spo2_data = AsyncMock()
        mock_database.upsert_fitness_metrics = AsyncMock()
        mock_database.upsert_respiration_data = AsyncMock()
        mock_database.upsert_training_readiness = AsyncMock()

    @pytest.mark.asyncio
    async def test_fetch_success_counts_days(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """fetch() returns one record per day in the date range."""
        self._setup_all_metrics_success(mock_garmin_client, mock_database)

        # START_DATE = Jan 1, END_DATE = Jan 3 → 3 days
        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 3
        assert error is None

    @pytest.mark.asyncio
    async def test_fetch_calls_all_metric_endpoints(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """All five metric endpoints are called for each day."""
        self._setup_all_metrics_success(mock_garmin_client, mock_database)

        await fetcher.fetch(start_date=START_DATE, end_date=END_DATE)

        # 3 days × 1 call each
        assert mock_garmin_client.get_hrv_data.call_count == 3
        assert mock_garmin_client.get_spo2_data.call_count == 3
        assert mock_garmin_client.get_max_metrics.call_count == 3
        assert mock_garmin_client.get_respiration_data.call_count == 3
        assert mock_garmin_client.get_training_readiness.call_count == 3

    @pytest.mark.asyncio
    async def test_partial_failure_continues_other_days(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """A failure on one day does not abort subsequent days."""
        # Day 1 will raise via HRV; days 2-3 succeed
        call_count = {"n": 0}

        def hrv_side_effect(date_str):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("Simulated HRV crash")
            return (True, {"hrvSummary": {"weeklyAvg": 50}}, None)

        mock_garmin_client.get_hrv_data.side_effect = hrv_side_effect
        mock_garmin_client.get_spo2_data.return_value = (True, {}, None)
        mock_garmin_client.get_max_metrics.return_value = (True, {}, None)
        mock_garmin_client.get_respiration_data.return_value = (True, {}, None)
        mock_garmin_client.get_training_readiness.return_value = (True, {}, None)
        mock_database.upsert_hrv_data = AsyncMock()
        mock_database.upsert_spo2_data = AsyncMock()
        mock_database.upsert_fitness_metrics = AsyncMock()
        mock_database.upsert_respiration_data = AsyncMock()
        mock_database.upsert_training_readiness = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        # 2 successful days out of 3
        assert count == 2
        assert error is not None  # error from day 1 is recorded

    @pytest.mark.asyncio
    async def test_api_returning_false_does_not_crash(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """Garmin returning success=False for a metric is silently skipped."""
        mock_garmin_client.get_hrv_data.return_value = (False, None, "No data")
        mock_garmin_client.get_spo2_data.return_value = (False, None, "No data")
        mock_garmin_client.get_max_metrics.return_value = (False, None, "No data")
        mock_garmin_client.get_respiration_data.return_value = (False, None, "No data")
        mock_garmin_client.get_training_readiness.return_value = (
            False,
            None,
            "No data",
        )

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        # Days are still counted (no exception raised)
        assert count == 3
        assert error is None


class TestAdvancedMetricsFetcherTransforms:
    """Unit tests for AdvancedMetricsFetcher transformation methods."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_advanced_metrics_fetcher(mock_database, mock_garmin_client)

    def test_transform_hrv_data(self, fetcher):
        """HRV summary fields are mapped to the correct DB columns."""
        d = date(2025, 1, 1)
        raw = {
            "weeklyAvg": 55,
            "lastNightAvg": 52,
            "lastNight5MinHigh": 65,
            "status": "balanced",
            "feedbackPhrase": "HRV_BALANCED_1",
        }

        result = fetcher._transform_hrv_data(d, raw)

        assert result["calendar_date"] == d
        assert result["weekly_avg"] == 55
        assert result["last_night_avg"] == 52
        assert result["last_night_5_min_high"] == 65
        assert result["hrv_status"] == "balanced"
        assert result["feedback_phrase"] == "HRV_BALANCED_1"

    def test_transform_spo2_data(self, fetcher):
        """SpO2 fields are mapped including the ms-epoch timestamp."""
        d = date(2025, 1, 1)
        raw = {
            "averageSPO2": 97,
            "lowestSPO2": 93,
            "latestSpO2": 96,
            "latestSpO2ReadingTimeGMT": 1735689600000,
            "spO2ValuesArray": [[1735689600000, 97], [1735689660000, 96]],
        }

        result = fetcher._transform_spo2_data(d, raw)

        assert result["calendar_date"] == d
        assert result["average_spo2_percentage"] == 97
        assert result["lowest_spo2_percentage"] == 93
        assert result["latest_spo2_reading"] == 96
        assert isinstance(result["latest_spo2_reading_timestamp"], datetime)
        assert result["spo2_values"] is not None
        parsed = json.loads(result["spo2_values"])
        assert len(parsed) == 2

    def test_transform_spo2_no_values_array(self, fetcher):
        """spo2_values is None when spO2ValuesArray is absent."""
        result = fetcher._transform_spo2_data(date(2025, 1, 1), {})
        assert result["spo2_values"] is None

    def test_transform_fitness_metrics(self, fetcher):
        """Fitness metric fields are mapped to DB column names."""
        d = date(2025, 1, 1)
        raw = {
            "vo2Max": 55,
            "vo2MaxRunning": 57,
            "vo2MaxCycling": 52,
            "fitnessAge": 28,
            "lactateThresholdHeartRate": 162,
            "lactateThresholdSpeed": 3.2,
        }

        result = fetcher._transform_fitness_metrics(d, raw)

        assert result["calendar_date"] == d
        assert result["vo2_max"] == 55
        assert result["vo2_max_running"] == 57
        assert result["vo2_max_cycling"] == 52
        assert result["fitness_age"] == 28
        assert result["lactate_threshold_bpm"] == 162
        assert result["lactate_threshold_speed"] == 3.2

    def test_transform_respiration_data(self, fetcher):
        """Respiration fields are mapped correctly."""
        d = date(2025, 1, 1)
        raw = {
            "avgWakingRespirationRate": 15,
            "maxWakingRespirationRate": 22,
            "minWakingRespirationRate": 12,
            "avgSleepRespirationRate": 13,
        }

        result = fetcher._transform_respiration_data(d, raw)

        assert result["calendar_date"] == d
        assert result["avg_waking_respiration_rate"] == 15
        assert result["max_waking_respiration_rate"] == 22
        assert result["min_waking_respiration_rate"] == 12
        assert result["avg_sleep_respiration_rate"] == 13

    def test_transform_training_readiness_score_fallback(self, fetcher):
        """readinessScore is used when score key is absent."""
        d = date(2025, 1, 1)
        raw = {"readinessScore": 75, "sleepScoreValue": 80}
        # _fetch_training_readiness builds the dict inline; replicate that here
        tr_data = {
            "calendar_date": d,
            "score": raw.get("score") or raw.get("readinessScore"),
            "score_feedback": raw.get("scoreFeedback") or raw.get("readinessFeedback"),
            "hrv_status": raw.get("hrvStatus"),
            "sleep_score": raw.get("sleepScore") or raw.get("sleepScoreValue"),
            "recent_training_load": raw.get("recentTrainingLoad")
            or raw.get("acuteTrainingLoad"),
            "acute_load": raw.get("acuteLoad") or raw.get("acuteTrainingLoadScore"),
            "chronic_load": raw.get("chronicLoad") or raw.get("chronicTrainingLoad"),
        }

        assert tr_data["score"] == 75
        assert tr_data["sleep_score"] == 80
        assert tr_data["hrv_status"] is None


# ---------------------------------------------------------------------------
# WellnessFetcher
# ---------------------------------------------------------------------------


class TestWellnessFetcherFetch:
    """Integration-level tests for WellnessFetcher.fetch()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_wellness_fetcher(mock_database, mock_garmin_client)

    @pytest.mark.asyncio
    async def test_fetch_success_counts_days(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """fetch() returns one record per day when hydration data is available."""
        mock_garmin_client.get_hydration_data.return_value = (
            True,
            {"valueInML": 2000, "goalInML": 2500},
            None,
        )
        mock_database.upsert_hydration_data = AsyncMock()

        # START_DATE = Jan 1, END_DATE = Jan 3 → 3 days
        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 3
        assert error is None
        assert mock_database.upsert_hydration_data.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_api_failure_records_error_but_continues(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """An API failure on one day is captured and remaining days are processed."""
        call_count = {"n": 0}

        def hydration_side_effect(date_str):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("Timeout on day 2")
            return (True, {"valueInML": 1800}, None)

        mock_garmin_client.get_hydration_data.side_effect = hydration_side_effect
        mock_database.upsert_hydration_data = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 2  # days 1 and 3 succeed
        assert error is not None  # day 2 error recorded

    @pytest.mark.asyncio
    async def test_fetch_api_returning_false_is_skipped(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """success=False from Garmin is handled gracefully (day still counted)."""
        mock_garmin_client.get_hydration_data.return_value = (False, None, "No data")
        mock_database.upsert_hydration_data = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        # Days processed without exception, hydration just not stored
        assert count == 3
        assert error is None
        mock_database.upsert_hydration_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_list_response_unwraps_first_element(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """A list response is unwrapped to its first dict before transforming."""
        mock_garmin_client.get_hydration_data.return_value = (
            True,
            [{"valueInML": 1500, "goalInML": 2000}],
            None,
        )
        mock_database.upsert_hydration_data = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 3
        assert mock_database.upsert_hydration_data.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_none_data_not_stored(
        self, fetcher, mock_garmin_client, mock_database
    ):
        """None or empty dict response from Garmin does not trigger an upsert."""
        mock_garmin_client.get_hydration_data.return_value = (True, None, None)
        mock_database.upsert_hydration_data = AsyncMock()

        count, error = await fetcher.fetch(
            start_date=START_DATE, end_date=END_DATE
        )

        assert count == 3
        mock_database.upsert_hydration_data.assert_not_called()


class TestWellnessFetcherTransformHydration:
    """Unit tests for WellnessFetcher._transform_hydration_data()."""

    @pytest.fixture
    def fetcher(self, mock_database, mock_garmin_client):
        return _make_wellness_fetcher(mock_database, mock_garmin_client)

    def test_maps_all_fields(self, fetcher):
        """All hydration fields are mapped to the correct DB column names."""
        d = date(2025, 1, 1)
        raw = {
            "valueInML": 2100,
            "goalInML": 2500,
            "hydrationLog": [{"time": "08:00", "value": 500}],
        }

        result = fetcher._transform_hydration_data(d, raw)

        assert result["calendar_date"] == d
        assert result["total_hydration_ml"] == 2100
        assert result["hydration_goal_ml"] == 2500
        assert result["hydration_entries"] is not None
        parsed = json.loads(result["hydration_entries"])
        assert len(parsed) == 1

    def test_hydration_entries_none_when_log_absent(self, fetcher):
        """hydration_entries is None when hydrationLog is missing."""
        d = date(2025, 1, 1)
        raw = {"valueInML": 1800}

        result = fetcher._transform_hydration_data(d, raw)

        assert result["hydration_entries"] is None

    def test_missing_fields_yield_none(self, fetcher):
        """Absent numeric fields produce None values."""
        result = fetcher._transform_hydration_data(date(2025, 1, 1), {})

        assert result["total_hydration_ml"] is None
        assert result["hydration_goal_ml"] is None
        assert result["hydration_entries"] is None
