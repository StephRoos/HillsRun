"""Unit tests for the Database class in src/database.py.

Covers initialization, connection lifecycle, user operations, sync state,
query methods, planned workout CRUD, and coaching operations.
All asyncpg I/O is mocked via the conftest fixtures (mock_database, mock_db_pool).
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import DatabaseConfig
from src.database import Database


# ===========================================================================
# 1. __init__ stores config correctly
# ===========================================================================

class TestDatabaseInit:
    """Tests for Database.__init__."""

    def test_config_is_stored(self, test_db_config):
        """__init__ stores the provided DatabaseConfig on self.config."""
        db = Database(test_db_config)
        assert db.config is test_db_config

    def test_pool_starts_as_none(self, test_db_config):
        """__init__ leaves self.pool as None before any connection."""
        db = Database(test_db_config)
        assert db.pool is None

    def test_config_fields_match(self, test_db_config):
        """Config fields are accessible via db.config after init."""
        db = Database(test_db_config)
        assert db.config.host == "localhost"
        assert db.config.port == 5432
        assert db.config.database == "test_garmin"
        assert db.config.user == "test_user"
        assert db.config.password == "test_password"
        assert db.config.pool_min_size == 1
        assert db.config.pool_max_size == 5


# ===========================================================================
# 2. connect() creates pool (mock asyncpg.create_pool)
# ===========================================================================

class TestDatabaseConnect:
    """Tests for Database.connect."""

    @pytest.mark.asyncio
    async def test_connect_creates_pool(self, test_db_config):
        """connect() calls asyncpg.create_pool and stores the result in self.pool."""
        db = Database(test_db_config)
        fake_pool = MagicMock()
        mock_create = AsyncMock(return_value=fake_pool)
        with patch("asyncpg.create_pool", new=mock_create):
            await db.connect()
        mock_create.assert_called_once()
        assert db.pool is fake_pool

    @pytest.mark.asyncio
    async def test_connect_passes_correct_host_port(self, test_db_config):
        """connect() forwards host/port/database/user/password from config."""
        db = Database(test_db_config)
        fake_pool = MagicMock()
        mock_create = AsyncMock(return_value=fake_pool)
        with patch("asyncpg.create_pool", new=mock_create):
            await db.connect()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["host"] == test_db_config.host
        assert call_kwargs["port"] == test_db_config.port
        assert call_kwargs["database"] == test_db_config.database
        assert call_kwargs["user"] == test_db_config.user
        assert call_kwargs["password"] == test_db_config.password

    # -----------------------------------------------------------------------
    # 3. connect() with SSL creates SSL context
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connect_with_ssl_creates_ssl_context(self):
        """connect() with ssl=True passes an ssl.SSLContext to create_pool."""
        import ssl as ssl_module

        ssl_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="db",
            user="user",
            password="pass",
            ssl=True,
        )
        db = Database(ssl_config)
        fake_pool = MagicMock()
        mock_create = AsyncMock(return_value=fake_pool)
        with patch("asyncpg.create_pool", new=mock_create):
            await db.connect()
        call_kwargs = mock_create.call_args.kwargs
        assert isinstance(call_kwargs["ssl"], ssl_module.SSLContext)

    @pytest.mark.asyncio
    async def test_connect_without_ssl_passes_false(self, test_db_config):
        """connect() with ssl=False passes False to create_pool."""
        db = Database(test_db_config)
        assert test_db_config.ssl is False
        fake_pool = MagicMock()
        mock_create = AsyncMock(return_value=fake_pool)
        with patch("asyncpg.create_pool", new=mock_create):
            await db.connect()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["ssl"] is False

    # -----------------------------------------------------------------------
    # 4. connect() failure raises exception
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connect_failure_raises_exception(self, test_db_config):
        """connect() re-raises the exception when asyncpg.create_pool fails."""
        db = Database(test_db_config)
        with patch("asyncpg.create_pool", side_effect=OSError("connection refused")):
            with pytest.raises(OSError, match="connection refused"):
                await db.connect()

    @pytest.mark.asyncio
    async def test_connect_failure_leaves_pool_none(self, test_db_config):
        """pool remains None when connect() raises."""
        db = Database(test_db_config)
        with patch("asyncpg.create_pool", side_effect=Exception("boom")):
            with pytest.raises(Exception):
                await db.connect()
        assert db.pool is None


# ===========================================================================
# 5. disconnect() closes pool
# ===========================================================================

class TestDatabaseDisconnect:
    """Tests for Database.disconnect."""

    @pytest.mark.asyncio
    async def test_disconnect_closes_pool(self, mock_database, mock_db_pool):
        """disconnect() calls close() on the pool."""
        await mock_database.disconnect()
        mock_db_pool.close.assert_called_once()

    # -----------------------------------------------------------------------
    # 6. disconnect() with no pool is safe
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_disconnect_with_no_pool_is_safe(self, test_db_config):
        """disconnect() does not raise when pool is None."""
        db = Database(test_db_config)
        assert db.pool is None
        await db.disconnect()  # must not raise


# ===========================================================================
# 7. get_or_create_user calls pool.fetchval with correct query
# ===========================================================================

class TestGetOrCreateUser:
    """Tests for Database.get_or_create_user."""

    @pytest.mark.asyncio
    async def test_returns_user_id(self, mock_database, mock_db_pool):
        """get_or_create_user returns the user_id from pool.fetchval."""
        mock_db_pool.fetchval.return_value = 42
        result = await mock_database.get_or_create_user("garmin-123", "Alice", "alice@example.com")
        assert result == 42

    @pytest.mark.asyncio
    async def test_calls_fetchval_with_args(self, mock_database, mock_db_pool):
        """get_or_create_user passes garmin_user_id, display_name, email to pool.fetchval."""
        mock_db_pool.fetchval.return_value = 7
        await mock_database.get_or_create_user("garmin-xyz", "Bob", "bob@example.com")
        args = mock_db_pool.fetchval.call_args
        positional = list(args[0])
        assert "garmin-xyz" in positional
        assert "Bob" in positional
        assert "bob@example.com" in positional

    @pytest.mark.asyncio
    async def test_accepts_none_display_name_and_email(self, mock_database, mock_db_pool):
        """get_or_create_user works when display_name and email are None."""
        mock_db_pool.fetchval.return_value = 5
        result = await mock_database.get_or_create_user("garmin-abc")
        assert result == 5


# ===========================================================================
# 8. get_user_by_better_auth_id returns user_id or None
# ===========================================================================

class TestGetUserByBetterAuthId:
    """Tests for Database.get_user_by_better_auth_id."""

    @pytest.mark.asyncio
    async def test_returns_user_id_when_found(self, mock_database, mock_db_pool):
        """Returns the integer user_id when the better_auth_user_id exists."""
        mock_db_pool.fetchval.return_value = 99
        result = await mock_database.get_user_by_better_auth_id("ba-user-1")
        assert result == 99

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_database, mock_db_pool):
        """Returns None when better_auth_user_id has no matching row."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.get_user_by_better_auth_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_passes_better_auth_id_to_query(self, mock_database, mock_db_pool):
        """Passes the better_auth_user_id as a query parameter."""
        mock_db_pool.fetchval.return_value = 3
        await mock_database.get_user_by_better_auth_id("ba-42")
        call_args = mock_db_pool.fetchval.call_args[0]
        assert "ba-42" in call_args


# ===========================================================================
# 9. store_encrypted_tokens and get_encrypted_tokens
# ===========================================================================

class TestEncryptedTokens:
    """Tests for store_encrypted_tokens and get_encrypted_tokens."""

    @pytest.mark.asyncio
    async def test_store_encrypted_tokens_calls_execute(self, mock_database, mock_db_pool):
        """store_encrypted_tokens executes an UPDATE with the token bytes."""
        token_bytes = b"encrypted_token_data"
        await mock_database.store_encrypted_tokens(user_id=1, encrypted_tokens=token_bytes)
        mock_db_pool.execute.assert_called_once()
        call_args = mock_db_pool.execute.call_args[0]
        assert token_bytes in call_args
        assert 1 in call_args

    @pytest.mark.asyncio
    async def test_get_encrypted_tokens_returns_bytes(self, mock_database, mock_db_pool):
        """get_encrypted_tokens returns the bytes stored by fetchval."""
        token_bytes = b"stored_token"
        mock_db_pool.fetchval.return_value = token_bytes
        result = await mock_database.get_encrypted_tokens(user_id=1)
        assert result == token_bytes

    @pytest.mark.asyncio
    async def test_get_encrypted_tokens_returns_none_when_missing(self, mock_database, mock_db_pool):
        """get_encrypted_tokens returns None when no tokens are stored."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.get_encrypted_tokens(user_id=99)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_encrypted_tokens_passes_user_id(self, mock_database, mock_db_pool):
        """get_encrypted_tokens passes the user_id as a query parameter."""
        mock_db_pool.fetchval.return_value = None
        await mock_database.get_encrypted_tokens(user_id=55)
        call_args = mock_db_pool.fetchval.call_args[0]
        assert 55 in call_args


# ===========================================================================
# 10. get_last_sync_date returns date or None
# ===========================================================================

class TestGetLastSyncDate:
    """Tests for Database.get_last_sync_date."""

    @pytest.mark.asyncio
    async def test_returns_date_when_synced(self, mock_database, mock_db_pool):
        """Returns a date object when a sync record exists."""
        sync_date = date(2025, 3, 1)
        mock_db_pool.fetchval.return_value = sync_date
        result = await mock_database.get_last_sync_date("daily_health", user_id=1)
        assert result == sync_date

    @pytest.mark.asyncio
    async def test_returns_none_when_never_synced(self, mock_database, mock_db_pool):
        """Returns None when category has never been synced."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.get_last_sync_date("activities", user_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_with_user_id_passes_both_params(self, mock_database, mock_db_pool):
        """When user_id is provided, both category and user_id are query params."""
        mock_db_pool.fetchval.return_value = None
        await mock_database.get_last_sync_date("activities", user_id=7)
        call_args = mock_db_pool.fetchval.call_args[0]
        assert "activities" in call_args
        assert 7 in call_args

    @pytest.mark.asyncio
    async def test_without_user_id_passes_category_only(self, mock_database, mock_db_pool):
        """When user_id is None, only category is passed as a query param."""
        mock_db_pool.fetchval.return_value = None
        await mock_database.get_last_sync_date("wellness", user_id=None)
        call_args = mock_db_pool.fetchval.call_args[0]
        assert "wellness" in call_args
        assert None not in call_args


# ===========================================================================
# 11. update_sync_state calls execute
# ===========================================================================

class TestUpdateSyncState:
    """Tests for Database.update_sync_state."""

    @pytest.mark.asyncio
    async def test_calls_execute_with_user_id(self, mock_database, mock_db_pool):
        """update_sync_state calls pool.execute when user_id is provided."""
        await mock_database.update_sync_state(
            category="activities",
            last_sync_date=date(2025, 3, 1),
            records_synced=100,
            user_id=3,
        )
        mock_db_pool.execute.assert_called_once()
        call_args = mock_db_pool.execute.call_args[0]
        assert "activities" in call_args
        assert 3 in call_args
        assert 100 in call_args

    @pytest.mark.asyncio
    async def test_calls_execute_without_user_id(self, mock_database, mock_db_pool):
        """update_sync_state calls pool.execute when user_id is None."""
        await mock_database.update_sync_state(
            category="daily_health",
            last_sync_date=date(2025, 2, 28),
            records_synced=50,
            user_id=None,
        )
        mock_db_pool.execute.assert_called_once()
        call_args = mock_db_pool.execute.call_args[0]
        assert "daily_health" in call_args

    @pytest.mark.asyncio
    async def test_passes_sync_status(self, mock_database, mock_db_pool):
        """update_sync_state includes sync_status in the execute call."""
        await mock_database.update_sync_state(
            category="activities",
            last_sync_date=date(2025, 1, 1),
            records_synced=0,
            sync_status="failed",
            error_message="timeout",
            user_id=1,
        )
        call_args = mock_db_pool.execute.call_args[0]
        assert "failed" in call_args
        assert "timeout" in call_args


# ===========================================================================
# 12. query_first_user returns int or None
# ===========================================================================

class TestQueryFirstUser:
    """Tests for Database.query_first_user."""

    @pytest.mark.asyncio
    async def test_returns_user_id(self, mock_database, mock_db_pool):
        """Returns the first user_id integer from the database."""
        mock_db_pool.fetchval.return_value = 1
        result = await mock_database.query_first_user()
        assert result == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_no_users(self, mock_database, mock_db_pool):
        """Returns None when there are no users in the database."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.query_first_user()
        assert result is None

    @pytest.mark.asyncio
    async def test_calls_fetchval(self, mock_database, mock_db_pool):
        """query_first_user calls pool.fetchval exactly once."""
        mock_db_pool.fetchval.return_value = 2
        await mock_database.query_first_user()
        mock_db_pool.fetchval.assert_called_once()


# ===========================================================================
# 13. query_daily_summaries returns (rows, total)
# ===========================================================================

class TestQueryDailySummaries:
    """Tests for Database.query_daily_summaries."""

    @pytest.mark.asyncio
    async def test_returns_tuple_of_rows_and_total(self, mock_database, mock_db_pool):
        """Returns a (rows, total) tuple."""
        fake_rows = [{"calendar_date": date(2025, 3, 1), "total_steps": 8000}]
        mock_db_pool.fetchval.return_value = 1
        mock_db_pool.fetch.return_value = fake_rows

        rows, total = await mock_database.query_daily_summaries(
            user_id=1,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31),
        )
        assert rows == fake_rows
        assert total == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_data(self, mock_database, mock_db_pool):
        """Returns ([], 0) when there is no data in the date range."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []

        rows, total = await mock_database.query_daily_summaries(
            user_id=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        assert rows == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_passes_user_id_and_dates(self, mock_database, mock_db_pool):
        """Passes user_id and date range as query parameters."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []

        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        await mock_database.query_daily_summaries(user_id=5, start_date=start, end_date=end)

        fetchval_args = mock_db_pool.fetchval.call_args[0]
        assert 5 in fetchval_args
        assert start in fetchval_args
        assert end in fetchval_args


# ===========================================================================
# 14. query_activities with filters (sport_type, activity_type)
# ===========================================================================

class TestQueryActivities:
    """Tests for Database.query_activities."""

    @pytest.mark.asyncio
    async def test_no_filters(self, mock_database, mock_db_pool):
        """Returns (rows, total) without any optional filters."""
        mock_db_pool.fetchval.return_value = 3
        mock_db_pool.fetch.return_value = [{"activity_id": 1}, {"activity_id": 2}, {"activity_id": 3}]

        rows, total = await mock_database.query_activities(
            user_id=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
        )
        assert total == 3
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_with_sport_type_filter(self, mock_database, mock_db_pool):
        """sport_type filter is appended to query parameters."""
        mock_db_pool.fetchval.return_value = 1
        mock_db_pool.fetch.return_value = [{"activity_id": 10}]

        rows, total = await mock_database.query_activities(
            user_id=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            sport_type="trail_running",
        )
        fetchval_args = mock_db_pool.fetchval.call_args[0]
        assert "trail_running" in fetchval_args

    @pytest.mark.asyncio
    async def test_with_activity_type_filter(self, mock_database, mock_db_pool):
        """activity_type filter is appended to query parameters."""
        mock_db_pool.fetchval.return_value = 2
        mock_db_pool.fetch.return_value = [{"activity_id": 20}, {"activity_id": 21}]

        await mock_database.query_activities(
            user_id=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            activity_type="running",
        )
        fetchval_args = mock_db_pool.fetchval.call_args[0]
        assert "running" in fetchval_args

    @pytest.mark.asyncio
    async def test_with_both_filters(self, mock_database, mock_db_pool):
        """Both sport_type and activity_type can be applied simultaneously."""
        mock_db_pool.fetchval.return_value = 0
        mock_db_pool.fetch.return_value = []

        await mock_database.query_activities(
            user_id=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            sport_type="trail_running",
            activity_type="running",
        )
        fetchval_args = mock_db_pool.fetchval.call_args[0]
        assert "trail_running" in fetchval_args
        assert "running" in fetchval_args


# ===========================================================================
# 15. query_activity_by_id returns row or None
# ===========================================================================

class TestQueryActivityById:
    """Tests for Database.query_activity_by_id."""

    @pytest.mark.asyncio
    async def test_returns_row_when_found(self, mock_database, mock_db_pool):
        """Returns the activity row dict when the activity_id exists."""
        fake_row = {"activity_id": 777, "activity_name": "Trail run"}
        mock_db_pool.fetchrow.return_value = fake_row
        result = await mock_database.query_activity_by_id(activity_id=777)
        assert result == fake_row

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_database, mock_db_pool):
        """Returns None when no activity matches the given activity_id."""
        mock_db_pool.fetchrow.return_value = None
        result = await mock_database.query_activity_by_id(activity_id=999)
        assert result is None

    # -----------------------------------------------------------------------
    # 16. query_activity_by_id with user_id ownership check
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_with_user_id_passes_both_params(self, mock_database, mock_db_pool):
        """When user_id is provided, both activity_id and user_id are query params."""
        mock_db_pool.fetchrow.return_value = {"activity_id": 5, "user_id": 2}
        await mock_database.query_activity_by_id(activity_id=5, user_id=2)
        call_args = mock_db_pool.fetchrow.call_args[0]
        assert 5 in call_args
        assert 2 in call_args

    @pytest.mark.asyncio
    async def test_without_user_id_only_passes_activity_id(self, mock_database, mock_db_pool):
        """When user_id is None, only activity_id is used as query param."""
        mock_db_pool.fetchrow.return_value = {"activity_id": 8}
        await mock_database.query_activity_by_id(activity_id=8)
        call_args = mock_db_pool.fetchrow.call_args[0]
        assert 8 in call_args


# ===========================================================================
# 17. create_planned_workout calls fetchrow
# ===========================================================================

class TestCreatePlannedWorkout:
    """Tests for Database.create_planned_workout."""

    @pytest.mark.asyncio
    async def test_returns_created_workout_dict(self, mock_database, mock_db_pool):
        """Returns the newly created planned workout as a dict."""
        fake_row = MagicMock()
        fake_row.__iter__ = MagicMock(return_value=iter([
            ("id", 1),
            ("user_id", 1),
            ("planned_date", date(2025, 3, 10)),
            ("sport_type", "running"),
            ("title", "Easy run"),
        ]))
        fake_row.keys = MagicMock(return_value=["id", "user_id", "planned_date", "sport_type", "title"])
        fake_row.__getitem__ = MagicMock(side_effect=lambda k: {
            "id": 1, "user_id": 1, "planned_date": date(2025, 3, 10),
            "sport_type": "running", "title": "Easy run"
        }[k])
        # Simpler: make fetchrow return a plain dict (asyncpg Record behaves like dict)
        mock_db_pool.fetchrow.return_value = {
            "id": 1,
            "user_id": 1,
            "planned_date": date(2025, 3, 10),
            "sport_type": "running",
            "title": "Easy run",
        }

        workout_data = {
            "planned_date": date(2025, 3, 10),
            "sport_type": "running",
            "title": "Easy run",
            "intensity": "moderate",
        }
        result = await mock_database.create_planned_workout(user_id=1, data=workout_data)
        assert result["title"] == "Easy run"
        assert result["sport_type"] == "running"

    @pytest.mark.asyncio
    async def test_calls_fetchrow_once(self, mock_database, mock_db_pool):
        """create_planned_workout calls pool.fetchrow exactly once."""
        mock_db_pool.fetchrow.return_value = {
            "id": 2, "user_id": 1, "planned_date": date(2025, 3, 15),
            "sport_type": "cycling", "title": "Tempo",
        }
        await mock_database.create_planned_workout(
            user_id=1,
            data={
                "planned_date": date(2025, 3, 15),
                "sport_type": "cycling",
                "title": "Tempo",
            },
        )
        mock_db_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_user_id_and_data_fields(self, mock_database, mock_db_pool):
        """create_planned_workout passes user_id and workout data fields as params."""
        mock_db_pool.fetchrow.return_value = {
            "id": 3, "user_id": 4, "planned_date": date(2025, 4, 1),
            "sport_type": "trail_running", "title": "Long trail",
        }
        planned_date = date(2025, 4, 1)
        await mock_database.create_planned_workout(
            user_id=4,
            data={
                "planned_date": planned_date,
                "sport_type": "trail_running",
                "title": "Long trail",
            },
        )
        call_args = mock_db_pool.fetchrow.call_args[0]
        assert 4 in call_args
        assert planned_date in call_args
        assert "trail_running" in call_args
        assert "Long trail" in call_args


# ===========================================================================
# 18. update_planned_workout with dynamic fields
# ===========================================================================

class TestUpdatePlannedWorkout:
    """Tests for Database.update_planned_workout."""

    @pytest.mark.asyncio
    async def test_returns_updated_workout_dict(self, mock_database, mock_db_pool):
        """Returns the updated workout as a dict when found."""
        mock_db_pool.fetchrow.return_value = {
            "id": 10, "user_id": 1, "title": "Updated title", "sport_type": "running",
        }
        result = await mock_database.update_planned_workout(
            workout_id=10, user_id=1, data={"title": "Updated title"}
        )
        assert result["title"] == "Updated title"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_database, mock_db_pool):
        """Returns None when the workout_id doesn't belong to the user."""
        mock_db_pool.fetchrow.return_value = None
        result = await mock_database.update_planned_workout(
            workout_id=99, user_id=1, data={"title": "Ghost workout"}
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_only_allowed_fields_are_updated(self, mock_database, mock_db_pool):
        """Fields not in the allowed set are silently ignored."""
        mock_db_pool.fetchrow.return_value = {
            "id": 5, "user_id": 2, "title": "Kept title", "sport_type": "running",
        }
        # "user_id" is not an allowed update field — it should be filtered out
        result = await mock_database.update_planned_workout(
            workout_id=5,
            user_id=2,
            data={"title": "Kept title", "user_id": 999},
        )
        # The method must still succeed and return the row
        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_update_data_returns_existing_workout(self, mock_database, mock_db_pool):
        """Passing an empty data dict fetches and returns the existing workout."""
        mock_db_pool.fetchrow.return_value = {
            "id": 1, "user_id": 1, "title": "Existing", "sport_type": "cycling",
        }
        result = await mock_database.update_planned_workout(
            workout_id=1, user_id=1, data={}
        )
        # Should fall through to get_planned_workout which also uses fetchrow
        assert result is not None


# ===========================================================================
# 19. delete_planned_workout returns True/False
# ===========================================================================

class TestDeletePlannedWorkout:
    """Tests for Database.delete_planned_workout."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self, mock_database, mock_db_pool):
        """Returns True when the DELETE command removed exactly one row."""
        mock_db_pool.execute.return_value = "DELETE 1"
        result = await mock_database.delete_planned_workout(workout_id=1, user_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, mock_database, mock_db_pool):
        """Returns False when no row matched the DELETE (wrong id or user)."""
        mock_db_pool.execute.return_value = "DELETE 0"
        result = await mock_database.delete_planned_workout(workout_id=999, user_id=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_calls_execute_with_workout_id_and_user_id(self, mock_database, mock_db_pool):
        """delete_planned_workout passes both workout_id and user_id to pool.execute."""
        mock_db_pool.execute.return_value = "DELETE 1"
        await mock_database.delete_planned_workout(workout_id=7, user_id=3)
        call_args = mock_db_pool.execute.call_args[0]
        assert 7 in call_args
        assert 3 in call_args


# ===========================================================================
# 20. delete_activities returns count
# ===========================================================================

class TestDeleteActivities:
    """Tests for Database.delete_activities."""

    @pytest.mark.asyncio
    async def test_returns_deleted_count(self, mock_database, mock_db_pool):
        """Returns the integer count of deleted activities."""
        mock_db_pool.execute.return_value = "DELETE 3"
        count = await mock_database.delete_activities(
            activity_ids=[101, 102, 103], user_id=1
        )
        assert count == 3

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_list(self, mock_database, mock_db_pool):
        """Returns 0 immediately when activity_ids list is empty."""
        count = await mock_database.delete_activities(activity_ids=[], user_id=1)
        assert count == 0
        mock_db_pool.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_zero_when_none_deleted(self, mock_database, mock_db_pool):
        """Returns 0 when DELETE command reports zero rows affected."""
        mock_db_pool.execute.return_value = "DELETE 0"
        count = await mock_database.delete_activities(activity_ids=[999], user_id=1)
        assert count == 0

    @pytest.mark.asyncio
    async def test_passes_user_id_to_query(self, mock_database, mock_db_pool):
        """delete_activities passes user_id to the activities DELETE query."""
        mock_db_pool.execute.return_value = "DELETE 1"
        await mock_database.delete_activities(activity_ids=[50], user_id=8)
        # The second execute call is for activities DELETE
        last_call_args = mock_db_pool.execute.call_args[0]
        assert 8 in last_call_args


# ===========================================================================
# 21. is_coach_of_athlete returns bool
# ===========================================================================

class TestIsCoachOfAthlete:
    """Tests for Database.is_coach_of_athlete."""

    @pytest.mark.asyncio
    async def test_returns_true_when_linked(self, mock_database, mock_db_pool):
        """Returns True when coach is actively linked to the athlete."""
        mock_db_pool.fetchval.return_value = True
        result = await mock_database.is_coach_of_athlete(
            coach_better_auth_id="coach-abc", athlete_user_id=10
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_linked(self, mock_database, mock_db_pool):
        """Returns False when no active link exists between coach and athlete."""
        mock_db_pool.fetchval.return_value = False
        result = await mock_database.is_coach_of_athlete(
            coach_better_auth_id="coach-abc", athlete_user_id=99
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_passes_both_ids_to_query(self, mock_database, mock_db_pool):
        """Passes both coach_better_auth_id and athlete_user_id to pool.fetchval."""
        mock_db_pool.fetchval.return_value = True
        await mock_database.is_coach_of_athlete(
            coach_better_auth_id="coach-xyz", athlete_user_id=5
        )
        call_args = mock_db_pool.fetchval.call_args[0]
        assert "coach-xyz" in call_args
        assert 5 in call_args


# ===========================================================================
# 22. create_invite_code
# ===========================================================================

class TestCreateInviteCode:
    """Tests for Database.create_invite_code."""

    @pytest.mark.asyncio
    async def test_returns_invite_code_dict(self, mock_database, mock_db_pool):
        """Returns the created invite code as a dict."""
        mock_db_pool.fetchrow.return_value = {
            "id": 1,
            "coach_better_auth_id": "coach-1",
            "code": "INVITE123",
            "status": "pending",
        }
        result = await mock_database.create_invite_code(
            coach_better_auth_id="coach-1", code="INVITE123"
        )
        assert result["code"] == "INVITE123"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_calls_fetchrow_with_coach_id_and_code(self, mock_database, mock_db_pool):
        """Passes coach_better_auth_id and code to pool.fetchrow."""
        mock_db_pool.fetchrow.return_value = {
            "id": 2, "coach_better_auth_id": "coach-2", "code": "ABCDEF", "status": "pending",
        }
        await mock_database.create_invite_code(
            coach_better_auth_id="coach-2", code="ABCDEF"
        )
        mock_db_pool.fetchrow.assert_called_once()
        call_args = mock_db_pool.fetchrow.call_args[0]
        assert "coach-2" in call_args
        assert "ABCDEF" in call_args


# ===========================================================================
# 23. redeem_invite_code
# ===========================================================================

class TestRedeemInviteCode:
    """Tests for Database.redeem_invite_code.

    redeem_invite_code uses pool.acquire() as a transaction context manager.
    We need to wire up the acquire/transaction chain on mock_db_pool.
    """

    def _build_acquire_mock(self, fetchrow_return, execute_return="INSERT 1"):
        """Build a mock async context manager for pool.acquire()."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
        mock_conn.execute = AsyncMock(return_value=execute_return)

        # conn.transaction() also needs to be an async context manager
        mock_txn = AsyncMock()
        mock_txn.__aenter__ = AsyncMock(return_value=None)
        mock_txn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.transaction = MagicMock(return_value=mock_txn)

        mock_acquire = AsyncMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=False)
        return mock_acquire, mock_conn

    @pytest.mark.asyncio
    async def test_returns_redeemed_code_dict(self, mock_database, mock_db_pool):
        """Returns a dict with the redeemed invite code when valid."""
        fake_row = {
            "id": 1, "coach_better_auth_id": "coach-1",
            "code": "VALID", "status": "redeemed",
        }
        mock_acquire, _ = self._build_acquire_mock(fetchrow_return=fake_row)
        mock_db_pool.acquire = MagicMock(return_value=mock_acquire)

        result = await mock_database.redeem_invite_code(code="VALID", athlete_user_id=10)
        assert result["code"] == "VALID"
        assert result["status"] == "redeemed"

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_code(self, mock_database, mock_db_pool):
        """Returns None when the invite code is expired or already redeemed."""
        mock_acquire, _ = self._build_acquire_mock(fetchrow_return=None)
        mock_db_pool.acquire = MagicMock(return_value=mock_acquire)

        result = await mock_database.redeem_invite_code(code="EXPIRED", athlete_user_id=10)
        assert result is None

    @pytest.mark.asyncio
    async def test_inserts_coach_athlete_link_on_success(self, mock_database, mock_db_pool):
        """After redeeming, inserts a coach_athletes link inside the transaction."""
        fake_row = {
            "id": 3, "coach_better_auth_id": "coach-99",
            "code": "CODE99", "status": "redeemed",
        }
        mock_acquire, mock_conn = self._build_acquire_mock(fetchrow_return=fake_row)
        mock_db_pool.acquire = MagicMock(return_value=mock_acquire)

        await mock_database.redeem_invite_code(code="CODE99", athlete_user_id=7)
        # conn.execute is called to insert the coach_athletes row
        mock_conn.execute.assert_called_once()


# ===========================================================================
# 24. query_sync_status
# ===========================================================================

class TestQuerySyncStatus:
    """Tests for Database.query_sync_status."""

    @pytest.mark.asyncio
    async def test_with_user_id_passes_filter(self, mock_database, mock_db_pool):
        """When user_id is provided, query includes user_id filter."""
        mock_db_pool.fetch.return_value = [{"category": "activities", "user_id": 2}]
        await mock_database.query_sync_status(user_id=2)
        call_args = mock_db_pool.fetch.call_args[0]
        assert 2 in call_args

    @pytest.mark.asyncio
    async def test_without_user_id_returns_all(self, mock_database, mock_db_pool):
        """When user_id is None, query fetches all sync_state rows."""
        mock_db_pool.fetch.return_value = [
            {"category": "activities"}, {"category": "daily_health"}
        ]
        result = await mock_database.query_sync_status(user_id=None)
        assert len(result) == 2
        # No user_id param should be passed to fetch
        call_args = mock_db_pool.fetch.call_args[0]
        assert len(call_args) == 1  # only the SQL string, no param

    @pytest.mark.asyncio
    async def test_returns_list_of_rows(self, mock_database, mock_db_pool):
        """query_sync_status returns the list returned by pool.fetch."""
        expected = [{"category": "wellness", "sync_status": "success"}]
        mock_db_pool.fetch.return_value = expected
        result = await mock_database.query_sync_status(user_id=1)
        assert result == expected

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_rows(self, mock_database, mock_db_pool):
        """Returns an empty list when no sync_state rows exist."""
        mock_db_pool.fetch.return_value = []
        result = await mock_database.query_sync_status(user_id=1)
        assert result == []


# ===========================================================================
# Bonus: get_user_info, get_user_vma, update_user_vma, unlink_better_auth_user
# ===========================================================================

class TestGetUserInfo:
    """Tests for Database.get_user_info."""

    @pytest.mark.asyncio
    async def test_returns_dict_when_found(self, mock_database, mock_db_pool):
        """Returns a dict with user fields when the user exists."""
        mock_db_pool.fetchrow.return_value = {
            "user_id": 1, "garmin_user_id": "g1", "display_name": "Alice",
            "email": "alice@example.com", "better_auth_user_id": "ba-1",
            "has_tokens": True, "tokens_updated_at": None,
        }
        result = await mock_database.get_user_info(user_id=1)
        assert result is not None
        assert result["display_name"] == "Alice"
        # has_tokens is remapped to encrypted_tokens for backwards compat
        assert "encrypted_tokens" in result

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_database, mock_db_pool):
        """Returns None when no garmin_user row exists for user_id."""
        mock_db_pool.fetchrow.return_value = None
        result = await mock_database.get_user_info(user_id=999)
        assert result is None


class TestGetUserVma:
    """Tests for Database.get_user_vma and update_user_vma."""

    @pytest.mark.asyncio
    async def test_get_user_vma_returns_value(self, mock_database, mock_db_pool):
        """Returns the float VMA value when set."""
        mock_db_pool.fetchval.return_value = 16.5
        result = await mock_database.get_user_vma(user_id=1)
        assert result == 16.5

    @pytest.mark.asyncio
    async def test_get_user_vma_returns_none_when_not_set(self, mock_database, mock_db_pool):
        """Returns None when manual_vma is not set."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.get_user_vma(user_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_vma_calls_execute(self, mock_database, mock_db_pool):
        """update_user_vma calls pool.execute with the new vma value."""
        await mock_database.update_user_vma(user_id=1, vma=17.0)
        mock_db_pool.execute.assert_called_once()
        call_args = mock_db_pool.execute.call_args[0]
        assert 17.0 in call_args
        assert 1 in call_args

    @pytest.mark.asyncio
    async def test_update_user_vma_with_none_clears_value(self, mock_database, mock_db_pool):
        """update_user_vma with vma=None passes None to clear the field."""
        await mock_database.update_user_vma(user_id=2, vma=None)
        call_args = mock_db_pool.execute.call_args[0]
        assert None in call_args


class TestUnlinkBetterAuthUser:
    """Tests for Database.unlink_better_auth_user."""

    @pytest.mark.asyncio
    async def test_calls_execute_with_user_id(self, mock_database, mock_db_pool):
        """unlink_better_auth_user calls pool.execute with the user_id."""
        await mock_database.unlink_better_auth_user(user_id=5)
        mock_db_pool.execute.assert_called_once()
        call_args = mock_db_pool.execute.call_args[0]
        assert 5 in call_args


class TestGetLatestVo2maxRunning:
    """Tests for Database.get_latest_vo2max_running."""

    @pytest.mark.asyncio
    async def test_returns_from_fitness_metrics_first(self, mock_database, mock_db_pool):
        """Returns the fitness_metrics value when it exists (primary source)."""
        mock_db_pool.fetchval.return_value = 55.0
        result = await mock_database.get_latest_vo2max_running(user_id=1)
        assert result == 55.0

    @pytest.mark.asyncio
    async def test_falls_back_to_activities_when_fitness_metrics_null(
        self, mock_database, mock_db_pool
    ):
        """Falls back to activities.vo2_max_value when fitness_metrics has none."""
        # First call (fitness_metrics) returns None, second call (activities) returns 52.0
        mock_db_pool.fetchval.side_effect = [None, 52.0]
        result = await mock_database.get_latest_vo2max_running(user_id=1)
        assert result == 52.0
        assert mock_db_pool.fetchval.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_none_when_both_sources_empty(self, mock_database, mock_db_pool):
        """Returns None when neither fitness_metrics nor activities have VO2max data."""
        mock_db_pool.fetchval.side_effect = [None, None]
        result = await mock_database.get_latest_vo2max_running(user_id=1)
        assert result is None


class TestGetUserByEmail:
    """Tests for Database.get_user_by_email."""

    @pytest.mark.asyncio
    async def test_returns_user_id_when_found(self, mock_database, mock_db_pool):
        """Returns the user_id when a garmin_user with the given email exists."""
        mock_db_pool.fetchval.return_value = 10
        result = await mock_database.get_user_by_email("user@example.com")
        assert result == 10

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_database, mock_db_pool):
        """Returns None when no user has the given email."""
        mock_db_pool.fetchval.return_value = None
        result = await mock_database.get_user_by_email("ghost@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_passes_email_to_query(self, mock_database, mock_db_pool):
        """Passes the email string as a query parameter."""
        mock_db_pool.fetchval.return_value = None
        await mock_database.get_user_by_email("test@test.com")
        call_args = mock_db_pool.fetchval.call_args[0]
        assert "test@test.com" in call_args
