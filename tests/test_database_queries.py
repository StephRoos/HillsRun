"""Additional unit tests for src/database.py to improve coverage.

Covers user operations, upsert methods, query methods, planned workout
operations, and coaching operations not already tested in test_database.py.
All asyncpg I/O is mocked via the conftest fixtures (mock_database, mock_db_pool).
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from src.database import Database


# ===========================================================================
# User Operations
# ===========================================================================


class TestGetUserByEmail:
    """Tests for Database.get_user_by_email."""

    @pytest.mark.asyncio
    async def test_returns_user_id_when_found(self, mock_database, mock_db_pool):
        """Returns the integer user_id when the email exists."""
        mock_db_pool.fetchval.return_value = 10
        result = await mock_database.get_user_by_email("alice@example.com")
        assert result == 10

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_database, mock_db_pool):
        """Returns None when no user with that email exists."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.get_user_by_email("ghost@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_passes_email_to_query(self, mock_database, mock_db_pool):
        """Passes the email as a query parameter."""
        mock_db_pool.fetchval.return_value = 5
        await mock_database.get_user_by_email("test@hillsrun.com")
        call_args = mock_db_pool.fetchval.call_args[0]
        assert "test@hillsrun.com" in call_args


def _make_acquire_mock(mock_db_pool, mock_conn):
    """Configure mock_db_pool.acquire() to work as an async context manager.

    asyncpg uses `async with pool.acquire() as conn`. The pool itself is an
    AsyncMock, so pool.acquire is also an AsyncMock — calling it returns a
    coroutine, not a context manager. We replace pool.acquire with a plain
    MagicMock so that pool.acquire() returns the context manager object
    synchronously, as asyncpg's real pool does.
    """
    acquire_ctx = MagicMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)
    # Use a plain MagicMock so calling acquire() returns the ctx directly
    mock_db_pool.acquire = MagicMock(return_value=acquire_ctx)


def _make_transaction_mock(mock_conn):
    """Configure mock_conn.transaction() to work as an async context manager.

    mock_conn is an AsyncMock, so calling mock_conn.transaction() normally
    returns a coroutine. Replace transaction with a plain MagicMock so that
    calling it returns the context manager object synchronously.
    """
    transaction_ctx = MagicMock()
    transaction_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    transaction_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=transaction_ctx)


class TestGetOrCreateUserWithLink:
    """Tests for Database.get_or_create_user_with_link."""

    @pytest.mark.asyncio
    async def test_returns_user_id(self, mock_database, mock_db_pool):
        """Returns the user_id from the upsert query."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        _make_transaction_mock(mock_conn)
        _make_acquire_mock(mock_db_pool, mock_conn)

        result = await mock_database.get_or_create_user_with_link(
            "garmin-111", "ba-user-1", "Alice", "alice@example.com"
        )
        assert result == 42

    @pytest.mark.asyncio
    async def test_clears_stale_link_before_upsert(self, mock_database, mock_db_pool):
        """Executes a stale-link clear UPDATE before upserting."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=7)
        _make_transaction_mock(mock_conn)
        _make_acquire_mock(mock_db_pool, mock_conn)

        await mock_database.get_or_create_user_with_link("garmin-222", "ba-user-2")

        # execute is called to clear stale link
        mock_conn.execute.assert_called_once()
        stale_args = mock_conn.execute.call_args[0]
        assert "ba-user-2" in stale_args
        assert "garmin-222" in stale_args

    @pytest.mark.asyncio
    async def test_passes_all_params_to_fetchval(self, mock_database, mock_db_pool):
        """Passes garmin_user_id, better_auth_user_id, display_name, email to fetchval."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=3)
        _make_transaction_mock(mock_conn)
        _make_acquire_mock(mock_db_pool, mock_conn)

        await mock_database.get_or_create_user_with_link(
            "g-333", "ba-333", "Bob", "bob@example.com"
        )
        fetchval_args = mock_conn.fetchval.call_args[0]
        assert "g-333" in fetchval_args
        assert "ba-333" in fetchval_args
        assert "Bob" in fetchval_args
        assert "bob@example.com" in fetchval_args

    @pytest.mark.asyncio
    async def test_accepts_none_display_name_and_email(self, mock_database, mock_db_pool):
        """Works when optional display_name and email are omitted."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        _make_transaction_mock(mock_conn)
        _make_acquire_mock(mock_db_pool, mock_conn)

        result = await mock_database.get_or_create_user_with_link("g-min", "ba-min")
        assert result == 1


class TestGetUserInfo:
    """Tests for Database.get_user_info."""

    @pytest.mark.asyncio
    async def test_returns_dict_when_user_exists(self, mock_database, mock_db_pool):
        """Returns a dict with user info when the row is found."""
        fake_row = {
            "user_id": 1,
            "garmin_user_id": "g-1",
            "display_name": "Alice",
            "email": "alice@example.com",
            "better_auth_user_id": "ba-1",
            "has_tokens": True,
            "tokens_updated_at": None,
        }
        mock_db_pool.fetchrow.return_value = fake_row
        result = await mock_database.get_user_info(1)
        assert result is not None
        assert result["user_id"] == 1
        # has_tokens is remapped to encrypted_tokens key
        assert "encrypted_tokens" in result

    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_found(self, mock_database, mock_db_pool):
        """Returns None when no row matches the user_id."""
        mock_db_pool.fetchrow.return_value = None
        result = await mock_database.get_user_info(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_remaps_has_tokens_key(self, mock_database, mock_db_pool):
        """has_tokens field from DB is renamed to encrypted_tokens in the result."""
        fake_row = {
            "user_id": 2,
            "garmin_user_id": "g-2",
            "display_name": "Bob",
            "email": "bob@example.com",
            "better_auth_user_id": "ba-2",
            "has_tokens": False,
            "tokens_updated_at": None,
        }
        mock_db_pool.fetchrow.return_value = fake_row
        result = await mock_database.get_user_info(2)
        assert "has_tokens" not in result
        assert result["encrypted_tokens"] is False

    @pytest.mark.asyncio
    async def test_passes_user_id_to_query(self, mock_database, mock_db_pool):
        """Passes user_id as a query parameter to fetchrow."""
        mock_db_pool.fetchrow.return_value = None
        await mock_database.get_user_info(77)
        call_args = mock_db_pool.fetchrow.call_args[0]
        assert 77 in call_args


# ===========================================================================
# Upsert Methods
# ===========================================================================


class TestUpsertDailySummary:
    """Tests for Database.upsert_daily_summary."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_daily_summary calls pool.execute once."""
        data = {
            "calendar_date": date(2025, 3, 1),
            "total_steps": 8000,
            "resting_heart_rate": 52,
        }
        await mock_database.upsert_daily_summary(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_user_id(self, mock_database, mock_db_pool):
        """user_id is included among the execute call parameters."""
        data = {"calendar_date": date(2025, 3, 1)}
        await mock_database.upsert_daily_summary(user_id=5, data=data)
        args = mock_db_pool.execute.call_args[0]
        assert 5 in args

    @pytest.mark.asyncio
    async def test_handles_missing_fields(self, mock_database, mock_db_pool):
        """Calling with an empty data dict does not raise."""
        await mock_database.upsert_daily_summary(user_id=1, data={})
        mock_db_pool.execute.assert_called_once()


class TestUpsertHeartRateSamples:
    """Tests for Database.upsert_heart_rate_samples."""

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_list(self, mock_database, mock_db_pool):
        """Returns 0 and does not call executemany when samples list is empty."""
        result = await mock_database.upsert_heart_rate_samples(user_id=1, samples=[])
        assert result == 0
        mock_db_pool.executemany.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_executemany_with_records(self, mock_database, mock_db_pool):
        """Calls executemany with the correct number of records."""
        mock_db_pool.executemany = AsyncMock()
        samples = [
            {"timestamp": "2025-03-01T08:00:00", "heart_rate": 65},
            {"timestamp": "2025-03-01T08:01:00", "heart_rate": 70},
        ]
        result = await mock_database.upsert_heart_rate_samples(user_id=1, samples=samples)
        assert result == 2
        mock_db_pool.executemany.assert_called_once()
        records = mock_db_pool.executemany.call_args[0][1]
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_record_tuple_contains_user_id(self, mock_database, mock_db_pool):
        """Each record tuple starts with user_id."""
        mock_db_pool.executemany = AsyncMock()
        samples = [{"timestamp": "2025-03-01T09:00:00", "heart_rate": 60}]
        await mock_database.upsert_heart_rate_samples(user_id=42, samples=samples)
        records = mock_db_pool.executemany.call_args[0][1]
        assert records[0][0] == 42


class TestUpsertSleepData:
    """Tests for Database.upsert_sleep_data."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_sleep_data calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "total_sleep_seconds": 28800}
        await mock_database.upsert_sleep_data(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_calendar_date(self, mock_database, mock_db_pool):
        """calendar_date is passed as a query parameter."""
        d = date(2025, 3, 5)
        data = {"calendar_date": d}
        await mock_database.upsert_sleep_data(user_id=1, data=data)
        args = mock_db_pool.execute.call_args[0]
        assert d in args


class TestUpsertStressData:
    """Tests for Database.upsert_stress_data."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_stress_data calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "average_stress_level": 35}
        await mock_database.upsert_stress_data(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_user_id_and_date(self, mock_database, mock_db_pool):
        """user_id and calendar_date are among the execute call parameters."""
        d = date(2025, 4, 1)
        await mock_database.upsert_stress_data(user_id=9, data={"calendar_date": d})
        args = mock_db_pool.execute.call_args[0]
        assert 9 in args
        assert d in args


class TestUpsertBodyBattery:
    """Tests for Database.upsert_body_battery."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_body_battery calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "charged_value": 95}
        await mock_database.upsert_body_battery(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_correct_number_of_args(self, mock_database, mock_db_pool):
        """Passes 9 positional parameters (query + 9 values) to execute."""
        data = {
            "calendar_date": date(2025, 3, 1),
            "charged_value": 80,
            "drained_value": 20,
            "highest_value": 95,
            "lowest_value": 40,
            "start_timestamp": None,
            "end_timestamp": None,
            "body_battery_values": None,
        }
        await mock_database.upsert_body_battery(user_id=1, data=data)
        args = mock_db_pool.execute.call_args[0]
        # query string + user_id + 8 data fields = 10 positional args
        assert len(args) == 10


class TestUpsertBodyComposition:
    """Tests for Database.upsert_body_composition."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_body_composition calls pool.execute once."""
        data = {"timestamp": "2025-03-01T08:00:00", "weight_kg": 72.5}
        await mock_database.upsert_body_composition(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_user_id(self, mock_database, mock_db_pool):
        """user_id is among the execute call parameters."""
        await mock_database.upsert_body_composition(user_id=33, data={})
        args = mock_db_pool.execute.call_args[0]
        assert 33 in args


class TestUpsertHrvData:
    """Tests for Database.upsert_hrv_data."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_hrv_data calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "weekly_avg": 55}
        await mock_database.upsert_hrv_data(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_hrv_fields(self, mock_database, mock_db_pool):
        """hrv_status and feedback_phrase are forwarded to execute."""
        data = {
            "calendar_date": date(2025, 3, 1),
            "hrv_status": "balanced",
            "feedback_phrase": "good",
        }
        await mock_database.upsert_hrv_data(user_id=1, data=data)
        args = mock_db_pool.execute.call_args[0]
        assert "balanced" in args
        assert "good" in args


class TestUpsertSpo2Data:
    """Tests for Database.upsert_spo2_data."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_spo2_data calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "average_spo2_percentage": 98}
        await mock_database.upsert_spo2_data(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()


class TestUpsertFitnessMetrics:
    """Tests for Database.upsert_fitness_metrics."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_fitness_metrics calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "vo2_max_running": 55.0}
        await mock_database.upsert_fitness_metrics(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_vo2_max_fields(self, mock_database, mock_db_pool):
        """vo2_max and related fields are forwarded to execute."""
        data = {
            "calendar_date": date(2025, 3, 1),
            "vo2_max": 52.0,
            "vo2_max_running": 53.0,
            "vo2_max_cycling": 48.0,
        }
        await mock_database.upsert_fitness_metrics(user_id=1, data=data)
        args = mock_db_pool.execute.call_args[0]
        assert 52.0 in args
        assert 53.0 in args
        assert 48.0 in args


class TestUpsertRespirationData:
    """Tests for Database.upsert_respiration_data."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_respiration_data calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "avg_waking_respiration_rate": 16}
        await mock_database.upsert_respiration_data(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()


class TestUpsertTrainingReadiness:
    """Tests for Database.upsert_training_readiness."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_training_readiness calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "score": 75}
        await mock_database.upsert_training_readiness(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_score(self, mock_database, mock_db_pool):
        """The score value is passed as a query parameter."""
        data = {"calendar_date": date(2025, 3, 1), "score": 82}
        await mock_database.upsert_training_readiness(user_id=1, data=data)
        args = mock_db_pool.execute.call_args[0]
        assert 82 in args


class TestUpsertActivity:
    """Tests for Database.upsert_activity."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_activity calls pool.execute once."""
        data = {
            "activity_id": 12345,
            "activity_name": "Morning Run",
            "activity_type": "running",
            "sport_type": "RUNNING",
        }
        await mock_database.upsert_activity(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_user_id_and_activity_id(self, mock_database, mock_db_pool):
        """user_id and activity_id are among the execute call parameters."""
        data = {"activity_id": 99999}
        await mock_database.upsert_activity(user_id=7, data=data)
        args = mock_db_pool.execute.call_args[0]
        assert 7 in args
        assert 99999 in args

    @pytest.mark.asyncio
    async def test_handles_empty_data(self, mock_database, mock_db_pool):
        """Does not raise when data dict is empty (all fields default to None)."""
        await mock_database.upsert_activity(user_id=1, data={})
        mock_db_pool.execute.assert_called_once()


class TestUpsertActivitySplits:
    """Tests for Database.upsert_activity_splits."""

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_list(self, mock_database, mock_db_pool):
        """Returns 0 and does not call executemany when splits list is empty."""
        mock_db_pool.executemany = AsyncMock()
        result = await mock_database.upsert_activity_splits(activity_id=1, splits=[])
        assert result == 0
        mock_db_pool.executemany.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_executemany_with_splits(self, mock_database, mock_db_pool):
        """Calls executemany and returns correct count for a non-empty splits list."""
        mock_db_pool.executemany = AsyncMock()
        splits = [
            {"split_index": 0, "split_type": "lap", "distance_meters": 1000},
            {"split_index": 1, "split_type": "lap", "distance_meters": 1000},
            {"split_index": 2, "split_type": "lap", "distance_meters": 500},
        ]
        result = await mock_database.upsert_activity_splits(activity_id=555, splits=splits)
        assert result == 3
        mock_db_pool.executemany.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_starts_with_activity_id(self, mock_database, mock_db_pool):
        """First element of each record tuple is the activity_id."""
        mock_db_pool.executemany = AsyncMock()
        splits = [{"split_index": 0, "distance_meters": 500}]
        await mock_database.upsert_activity_splits(activity_id=777, splits=splits)
        records = mock_db_pool.executemany.call_args[0][1]
        assert records[0][0] == 777


class TestUpsertHydrationData:
    """Tests for Database.upsert_hydration_data."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """upsert_hydration_data calls pool.execute once."""
        data = {"calendar_date": date(2025, 3, 1), "total_hydration_ml": 2500}
        await mock_database.upsert_hydration_data(user_id=1, data=data)
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_hydration_fields(self, mock_database, mock_db_pool):
        """total_hydration_ml and hydration_goal_ml are forwarded to execute."""
        data = {
            "calendar_date": date(2025, 3, 1),
            "total_hydration_ml": 2000,
            "hydration_goal_ml": 2500,
        }
        await mock_database.upsert_hydration_data(user_id=1, data=data)
        args = mock_db_pool.execute.call_args[0]
        assert 2000 in args
        assert 2500 in args


# ===========================================================================
# Query Methods
# ===========================================================================


class TestQueryHeartRateSamples:
    """Tests for Database.query_heart_rate_samples."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 3
        fake_row = MagicMock()
        mock_db_pool.fetch.return_value = [fake_row, fake_row, fake_row]

        rows, total = await mock_database.query_heart_rate_samples(
            user_id=1,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 7),
        )
        assert total == 3
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_passes_pagination_params(self, mock_database, mock_db_pool):
        """limit and offset are forwarded to pool.fetch."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []

        await mock_database.query_heart_rate_samples(
            user_id=1,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 7),
            limit=100,
            offset=50,
        )
        fetch_args = mock_db_pool.fetch.call_args[0]
        assert 100 in fetch_args
        assert 50 in fetch_args

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_data(self, mock_database, mock_db_pool):
        """Returns ([], 0) when no heart rate samples exist."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []
        rows, total = await mock_database.query_heart_rate_samples(
            user_id=1, start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
        )
        assert rows == []
        assert total == 0


class TestQuerySleepData:
    """Tests for Database.query_sleep_data."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 7
        mock_db_pool.fetch.return_value = [MagicMock()] * 7
        rows, total = await mock_database.query_sleep_data(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 7)
        )
        assert total == 7
        assert len(rows) == 7

    @pytest.mark.asyncio
    async def test_passes_user_id_to_both_calls(self, mock_database, mock_db_pool):
        """user_id is passed to both the COUNT query and the SELECT query."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []
        await mock_database.query_sleep_data(
            user_id=99, start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
        )
        fetchval_args = mock_db_pool.fetchval.call_args[0]
        fetch_args = mock_db_pool.fetch.call_args[0]
        assert 99 in fetchval_args
        assert 99 in fetch_args


class TestQueryStressData:
    """Tests for Database.query_stress_data."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 5
        mock_db_pool.fetch.return_value = [MagicMock()] * 5
        rows, total = await mock_database.query_stress_data(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 5)
        )
        assert total == 5
        assert len(rows) == 5


class TestQueryBodyBattery:
    """Tests for Database.query_body_battery."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 4
        mock_db_pool.fetch.return_value = [MagicMock()] * 4
        rows, total = await mock_database.query_body_battery(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 4)
        )
        assert total == 4
        assert len(rows) == 4

    @pytest.mark.asyncio
    async def test_default_limit_offset(self, mock_database, mock_db_pool):
        """Default limit=50 and offset=0 are used when not specified."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []
        await mock_database.query_body_battery(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 7)
        )
        fetch_args = mock_db_pool.fetch.call_args[0]
        assert 50 in fetch_args
        assert 0 in fetch_args


class TestQueryBodyComposition:
    """Tests for Database.query_body_composition."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 2
        mock_db_pool.fetch.return_value = [MagicMock(), MagicMock()]
        rows, total = await mock_database.query_body_composition(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 7)
        )
        assert total == 2
        assert len(rows) == 2


class TestQueryHrvData:
    """Tests for Database.query_hrv_data."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 6
        mock_db_pool.fetch.return_value = [MagicMock()] * 6
        rows, total = await mock_database.query_hrv_data(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 6)
        )
        assert total == 6
        assert len(rows) == 6


class TestQuerySpo2Data:
    """Tests for Database.query_spo2_data."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 3
        mock_db_pool.fetch.return_value = [MagicMock()] * 3
        rows, total = await mock_database.query_spo2_data(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 3)
        )
        assert total == 3


class TestQueryFitnessMetrics:
    """Tests for Database.query_fitness_metrics."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 10
        mock_db_pool.fetch.return_value = [MagicMock()] * 10
        rows, total = await mock_database.query_fitness_metrics(
            user_id=1, start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
        )
        assert total == 10
        assert len(rows) == 10


class TestQueryRespirationData:
    """Tests for Database.query_respiration_data."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 8
        mock_db_pool.fetch.return_value = [MagicMock()] * 8
        rows, total = await mock_database.query_respiration_data(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 8)
        )
        assert total == 8
        assert len(rows) == 8


class TestQueryTrainingReadiness:
    """Tests for Database.query_training_readiness."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 5
        mock_db_pool.fetch.return_value = [MagicMock()] * 5
        rows, total = await mock_database.query_training_readiness(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 5)
        )
        assert total == 5
        assert len(rows) == 5

    @pytest.mark.asyncio
    async def test_passes_date_range_to_count_query(self, mock_database, mock_db_pool):
        """start_date and end_date are passed to the COUNT query."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []
        start = date(2025, 2, 1)
        end = date(2025, 2, 28)
        await mock_database.query_training_readiness(user_id=1, start_date=start, end_date=end)
        fetchval_args = mock_db_pool.fetchval.call_args[0]
        assert start in fetchval_args
        assert end in fetchval_args


class TestQueryHydrationData:
    """Tests for Database.query_hydration_data."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 2
        mock_db_pool.fetch.return_value = [MagicMock(), MagicMock()]
        rows, total = await mock_database.query_hydration_data(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 2)
        )
        assert total == 2
        assert len(rows) == 2


class TestQueryActivitySplits:
    """Tests for Database.query_activity_splits."""

    @pytest.mark.asyncio
    async def test_returns_splits_when_no_user_id(self, mock_database, mock_db_pool):
        """Returns splits directly when user_id is not provided."""
        fake_splits = [MagicMock(), MagicMock()]
        mock_db_pool.fetch.return_value = fake_splits
        result = await mock_database.query_activity_splits(activity_id=100)
        assert result == fake_splits

    @pytest.mark.asyncio
    async def test_returns_empty_when_activity_not_owned_by_user(
        self, mock_database, mock_db_pool
    ):
        """Returns [] when user_id is set but activity doesn't belong to the user."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.query_activity_splits(activity_id=100, user_id=5)
        assert result == []
        mock_db_pool.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_splits_when_activity_owned_by_user(
        self, mock_database, mock_db_pool
    ):
        """Returns splits when activity_id belongs to the given user_id."""
        mock_db_pool.fetchval.return_value = 100
        fake_splits = [MagicMock()]
        mock_db_pool.fetch.return_value = fake_splits
        result = await mock_database.query_activity_splits(activity_id=100, user_id=5)
        assert result == fake_splits


class TestUpdateActivityCustomName:
    """Tests for Database.update_activity_custom_name."""

    @pytest.mark.asyncio
    async def test_returns_true_when_updated(self, mock_database, mock_db_pool):
        """Returns True when pool.execute returns 'UPDATE 1'."""
        mock_db_pool.execute.return_value = "UPDATE 1"
        result = await mock_database.update_activity_custom_name(
            activity_id=10, custom_name="My Run", user_id=1
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, mock_database, mock_db_pool):
        """Returns False when pool.execute returns 'UPDATE 0' (no row matched)."""
        mock_db_pool.execute.return_value = "UPDATE 0"
        result = await mock_database.update_activity_custom_name(
            activity_id=999, custom_name="Ghost Run", user_id=1
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_without_user_id_calls_execute(self, mock_database, mock_db_pool):
        """Calls pool.execute without user_id filter when user_id is None."""
        mock_db_pool.execute.return_value = "UPDATE 1"
        result = await mock_database.update_activity_custom_name(
            activity_id=10, custom_name="Admin Edit"
        )
        assert result is True
        args = mock_db_pool.execute.call_args[0]
        # user_id not in args when omitted
        assert 10 in args
        assert "Admin Edit" in args

    @pytest.mark.asyncio
    async def test_with_user_id_passes_all_three_params(self, mock_database, mock_db_pool):
        """Passes custom_name, activity_id, and user_id when user_id is provided."""
        mock_db_pool.execute.return_value = "UPDATE 1"
        await mock_database.update_activity_custom_name(
            activity_id=20, custom_name="Trail Run", user_id=7
        )
        args = mock_db_pool.execute.call_args[0]
        assert "Trail Run" in args
        assert 20 in args
        assert 7 in args


# ===========================================================================
# Planned Workout Operations
# ===========================================================================


class TestGetPlannedWorkout:
    """Tests for Database.get_planned_workout."""

    @pytest.mark.asyncio
    async def test_returns_dict_when_found(self, mock_database, mock_db_pool):
        """Returns the workout as a dict when the row is found."""
        fake_row = {"id": 1, "user_id": 5, "title": "Easy Run", "sport_type": "RUNNING"}
        mock_db_pool.fetchrow.return_value = fake_row
        result = await mock_database.get_planned_workout(workout_id=1, user_id=5)
        assert result == dict(fake_row)

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_database, mock_db_pool):
        """Returns None when no matching workout is found."""
        mock_db_pool.fetchrow.return_value = None
        result = await mock_database.get_planned_workout(workout_id=999, user_id=5)
        assert result is None

    @pytest.mark.asyncio
    async def test_passes_workout_id_and_user_id(self, mock_database, mock_db_pool):
        """Passes workout_id and user_id to pool.fetchrow."""
        mock_db_pool.fetchrow.return_value = None
        await mock_database.get_planned_workout(workout_id=42, user_id=8)
        args = mock_db_pool.fetchrow.call_args[0]
        assert 42 in args
        assert 8 in args


class TestQueryPlannedWorkouts:
    """Tests for Database.query_planned_workouts."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        mock_db_pool.fetchval.return_value = 3
        mock_db_pool.fetch.return_value = [MagicMock()] * 3
        rows, total = await mock_database.query_planned_workouts(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 31)
        )
        assert total == 3
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_default_limit_200(self, mock_database, mock_db_pool):
        """Default limit=200 is used when not specified."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []
        await mock_database.query_planned_workouts(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 31)
        )
        fetch_args = mock_db_pool.fetch.call_args[0]
        assert 200 in fetch_args

    @pytest.mark.asyncio
    async def test_passes_user_id_and_dates(self, mock_database, mock_db_pool):
        """user_id, start_date, and end_date are forwarded to both queries."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []
        start = date(2025, 4, 1)
        end = date(2025, 4, 30)
        await mock_database.query_planned_workouts(user_id=11, start_date=start, end_date=end)
        fetchval_args = mock_db_pool.fetchval.call_args[0]
        assert 11 in fetchval_args
        assert start in fetchval_args
        assert end in fetchval_args


class TestBulkCreatePlannedWorkouts:
    """Tests for Database.bulk_create_planned_workouts."""

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_list(self, mock_database, mock_db_pool):
        """Returns 0 and does not call executemany when workouts list is empty."""
        mock_db_pool.executemany = AsyncMock()
        result = await mock_database.bulk_create_planned_workouts(user_id=1, workouts=[])
        assert result == 0
        mock_db_pool.executemany.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_executemany_with_correct_count(self, mock_database, mock_db_pool):
        """Calls executemany with a record for each workout."""
        mock_db_pool.executemany = AsyncMock()
        workouts = [
            {
                "planned_date": date(2025, 3, 1),
                "sport_type": "RUNNING",
                "title": "Easy Run",
            },
            {
                "planned_date": date(2025, 3, 3),
                "sport_type": "TRAIL_RUNNING",
                "title": "Trail Run",
            },
        ]
        result = await mock_database.bulk_create_planned_workouts(user_id=1, workouts=workouts)
        assert result == 2
        mock_db_pool.executemany.assert_called_once()
        records = mock_db_pool.executemany.call_args[0][1]
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_record_contains_user_id_and_title(self, mock_database, mock_db_pool):
        """Each record contains user_id and workout title."""
        mock_db_pool.executemany = AsyncMock()
        workouts = [
            {
                "planned_date": date(2025, 3, 1),
                "sport_type": "RUNNING",
                "title": "Morning Jog",
            }
        ]
        await mock_database.bulk_create_planned_workouts(user_id=3, workouts=workouts)
        records = mock_db_pool.executemany.call_args[0][1]
        assert records[0][0] == 3
        assert records[0][3] == "Morning Jog"

    @pytest.mark.asyncio
    async def test_passes_created_by_user_id(self, mock_database, mock_db_pool):
        """created_by_user_id coach parameter is included in each record."""
        mock_db_pool.executemany = AsyncMock()
        workouts = [
            {
                "planned_date": date(2025, 3, 1),
                "sport_type": "RUNNING",
                "title": "Coach Plan",
            }
        ]
        await mock_database.bulk_create_planned_workouts(
            user_id=1, workouts=workouts, created_by_user_id="coach-ba-id"
        )
        records = mock_db_pool.executemany.call_args[0][1]
        assert "coach-ba-id" in records[0]

    @pytest.mark.asyncio
    async def test_default_intensity_is_moderate(self, mock_database, mock_db_pool):
        """Workout without intensity field defaults to 'moderate' in the record."""
        mock_db_pool.executemany = AsyncMock()
        workouts = [
            {
                "planned_date": date(2025, 3, 1),
                "sport_type": "RUNNING",
                "title": "No Intensity",
            }
        ]
        await mock_database.bulk_create_planned_workouts(user_id=1, workouts=workouts)
        records = mock_db_pool.executemany.call_args[0][1]
        assert "moderate" in records[0]


class TestGetActivityIdsForRange:
    """Tests for Database.get_activity_ids_for_range."""

    @pytest.mark.asyncio
    async def test_returns_list_of_ids(self, mock_database, mock_db_pool):
        """Returns a list of activity_id integers."""
        row1 = {"activity_id": 101}
        row2 = {"activity_id": 202}
        mock_db_pool.fetch.return_value = [row1, row2]
        result = await mock_database.get_activity_ids_for_range(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 7)
        )
        assert result == [101, 202]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_activities(self, mock_database, mock_db_pool):
        """Returns an empty list when there are no matching activities."""
        mock_db_pool.fetch.return_value = []
        result = await mock_database.get_activity_ids_for_range(
            user_id=1, start_date=date(2025, 3, 1), end_date=date(2025, 3, 7)
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_user_id_and_dates(self, mock_database, mock_db_pool):
        """user_id, start_date, and end_date are forwarded to pool.fetch."""
        mock_db_pool.fetch.return_value = []
        start = date(2025, 1, 1)
        end = date(2025, 1, 31)
        await mock_database.get_activity_ids_for_range(
            user_id=12, start_date=start, end_date=end
        )
        fetch_args = mock_db_pool.fetch.call_args[0]
        assert 12 in fetch_args
        assert start in fetch_args
        assert end in fetch_args


# ===========================================================================
# Coaching Operations
# ===========================================================================


class TestGetAthletesForCoach:
    """Tests for Database.get_athletes_for_coach."""

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self, mock_database, mock_db_pool):
        """Returns a list of athlete dicts."""
        fake_row = {
            "athlete_user_id": 5,
            "display_name": "Alice",
            "email": "alice@example.com",
            "status": "active",
            "linked_at": None,
        }
        mock_db_pool.fetch.return_value = [fake_row]
        result = await mock_database.get_athletes_for_coach("coach-ba-1")
        assert len(result) == 1
        assert result[0]["athlete_user_id"] == 5

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_athletes(self, mock_database, mock_db_pool):
        """Returns an empty list when the coach has no athletes."""
        mock_db_pool.fetch.return_value = []
        result = await mock_database.get_athletes_for_coach("coach-ba-new")
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_coach_id_to_query(self, mock_database, mock_db_pool):
        """Passes the coach's Better-Auth ID to pool.fetch."""
        mock_db_pool.fetch.return_value = []
        await mock_database.get_athletes_for_coach("coach-abc")
        args = mock_db_pool.fetch.call_args[0]
        assert "coach-abc" in args


class TestGetCoachesForAthlete:
    """Tests for Database.get_coaches_for_athlete."""

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self, mock_database, mock_db_pool):
        """Returns a list of coach dicts."""
        fake_row = {
            "coach_better_auth_id": "coach-ba-1",
            "coach_name": "Coach Bob",
            "coach_email": "bob@coach.com",
            "status": "active",
            "linked_at": None,
        }
        mock_db_pool.fetch.return_value = [fake_row]
        result = await mock_database.get_coaches_for_athlete(athlete_user_id=5)
        assert len(result) == 1
        assert result[0]["coach_better_auth_id"] == "coach-ba-1"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_coaches(self, mock_database, mock_db_pool):
        """Returns an empty list when the athlete has no coaches."""
        mock_db_pool.fetch.return_value = []
        result = await mock_database.get_coaches_for_athlete(athlete_user_id=99)
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_athlete_user_id(self, mock_database, mock_db_pool):
        """Passes the athlete_user_id to pool.fetch."""
        mock_db_pool.fetch.return_value = []
        await mock_database.get_coaches_for_athlete(athlete_user_id=55)
        args = mock_db_pool.fetch.call_args[0]
        assert 55 in args


class TestUnlinkCoachAthlete:
    """Tests for Database.unlink_coach_athlete."""

    @pytest.mark.asyncio
    async def test_returns_true_when_unlinked(self, mock_database, mock_db_pool):
        """Returns True when pool.execute returns 'UPDATE 1'."""
        mock_db_pool.execute.return_value = "UPDATE 1"
        result = await mock_database.unlink_coach_athlete("coach-ba-1", athlete_user_id=5)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, mock_database, mock_db_pool):
        """Returns False when pool.execute returns 'UPDATE 0'."""
        mock_db_pool.execute.return_value = "UPDATE 0"
        result = await mock_database.unlink_coach_athlete("coach-ba-1", athlete_user_id=999)
        assert result is False

    @pytest.mark.asyncio
    async def test_passes_coach_id_and_athlete_id(self, mock_database, mock_db_pool):
        """Passes coach_better_auth_id and athlete_user_id to pool.execute."""
        mock_db_pool.execute.return_value = "UPDATE 1"
        await mock_database.unlink_coach_athlete("coach-xyz", athlete_user_id=7)
        args = mock_db_pool.execute.call_args[0]
        assert "coach-xyz" in args
        assert 7 in args


class TestGetInviteCodesForCoach:
    """Tests for Database.get_invite_codes_for_coach."""

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self, mock_database, mock_db_pool):
        """Returns a list of invite code dicts."""
        fake_row = {
            "id": 1,
            "coach_better_auth_id": "coach-ba-1",
            "code": "INVITE123",
            "status": "pending",
        }
        mock_db_pool.fetch.return_value = [fake_row]
        result = await mock_database.get_invite_codes_for_coach("coach-ba-1")
        assert len(result) == 1
        assert result[0]["code"] == "INVITE123"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_codes(self, mock_database, mock_db_pool):
        """Returns an empty list when the coach has no invite codes."""
        mock_db_pool.fetch.return_value = []
        result = await mock_database.get_invite_codes_for_coach("coach-new")
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_coach_id_to_query(self, mock_database, mock_db_pool):
        """Passes coach_better_auth_id to pool.fetch."""
        mock_db_pool.fetch.return_value = []
        await mock_database.get_invite_codes_for_coach("coach-qrs")
        args = mock_db_pool.fetch.call_args[0]
        assert "coach-qrs" in args


class TestRevokeInviteCode:
    """Tests for Database.revoke_invite_code."""

    @pytest.mark.asyncio
    async def test_returns_true_when_revoked(self, mock_database, mock_db_pool):
        """Returns True when pool.execute returns 'UPDATE 1'."""
        mock_db_pool.execute.return_value = "UPDATE 1"
        result = await mock_database.revoke_invite_code("CODE1", "coach-ba-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_revoked(self, mock_database, mock_db_pool):
        """Returns False when pool.execute returns 'UPDATE 0' (code not found/not pending)."""
        mock_db_pool.execute.return_value = "UPDATE 0"
        result = await mock_database.revoke_invite_code("BADCODE", "coach-ba-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_passes_code_and_coach_id(self, mock_database, mock_db_pool):
        """Passes both the code and coach_better_auth_id to pool.execute."""
        mock_db_pool.execute.return_value = "UPDATE 1"
        await mock_database.revoke_invite_code("MYCODE", "coach-999")
        args = mock_db_pool.execute.call_args[0]
        assert "MYCODE" in args
        assert "coach-999" in args


class TestEnableCoaching:
    """Tests for Database.enable_coaching."""

    @pytest.mark.asyncio
    async def test_calls_execute(self, mock_database, mock_db_pool):
        """enable_coaching calls pool.execute once."""
        await mock_database.enable_coaching("ba-user-1")
        mock_db_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_better_auth_user_id(self, mock_database, mock_db_pool):
        """Passes the better_auth_user_id to pool.execute."""
        await mock_database.enable_coaching("ba-coach-123")
        args = mock_db_pool.execute.call_args[0]
        assert "ba-coach-123" in args


class TestGetCoachingEnabled:
    """Tests for Database.get_coaching_enabled."""

    @pytest.mark.asyncio
    async def test_returns_true_when_enabled(self, mock_database, mock_db_pool):
        """Returns True when coaching_enabled is True in the DB."""
        mock_db_pool.fetchval.return_value = True
        result = await mock_database.get_coaching_enabled("ba-coach-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(self, mock_database, mock_db_pool):
        """Returns False when coaching_enabled is False in the DB."""
        mock_db_pool.fetchval.return_value = False
        result = await mock_database.get_coaching_enabled("ba-user-plain")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_null(self, mock_database, mock_db_pool):
        """Returns False when coaching_enabled is NULL (user not found)."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.get_coaching_enabled("ba-ghost")
        assert result is False

    @pytest.mark.asyncio
    async def test_passes_better_auth_user_id(self, mock_database, mock_db_pool):
        """Passes the better_auth_user_id to pool.fetchval."""
        mock_db_pool.fetchval.return_value = False
        await mock_database.get_coaching_enabled("ba-check-123")
        args = mock_db_pool.fetchval.call_args[0]
        assert "ba-check-123" in args
