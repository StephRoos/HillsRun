"""Integration tests for SyncManager orchestration with mocked fetchers."""

import os
import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Config, DatabaseConfig, GarminConfig, SyncConfig, LoggingConfig
from src.sync_manager import SyncManager
from src.token_manager import TokenManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def token_key():
    """Generate a test Fernet key."""
    return TokenManager.generate_key()


@pytest.fixture
def test_config(tmp_path, token_key):
    """Build a Config suitable for unit tests."""
    return Config(
        database=DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_garmin",
            user="test_user",
            password="test_pass",
        ),
        garmin=GarminConfig(
            tokens_dir=tmp_path / "tokens",
            email="test@test.com",
            password="test_pass",
            token_key=token_key,
        ),
        sync=SyncConfig(categories=["daily_health", "activities"]),
        logging=LoggingConfig(),
    )


@pytest.fixture
def mock_db():
    """Fully mocked Database instance."""
    db = AsyncMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.get_encrypted_tokens = AsyncMock(return_value=b"encrypted-tokens")
    db.store_encrypted_tokens = AsyncMock()
    db.get_or_create_user = AsyncMock(return_value=67)
    db.query_sync_status = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_garmin_client():
    """Mocked GarminClient."""
    client = MagicMock()
    client.connect = MagicMock()
    client.get_user_profile = MagicMock(
        return_value=(True, {"userId": "12345", "displayName": "Test User"}, None)
    )
    client.get_refreshed_tokens = MagicMock(return_value=b"fresh-tokens")
    return client


# ---------------------------------------------------------------------------
# SyncManager initialization tests
# ---------------------------------------------------------------------------


class TestSyncManagerInitialization:
    """Tests for SyncManager.initialize() with different modes."""

    @pytest.mark.asyncio
    async def test_initialize_per_user_no_tokens_raises(self, test_config, mock_db):
        """initialize() with user_id raises when no tokens in DB."""
        mock_db.get_encrypted_tokens = AsyncMock(return_value=None)

        manager = SyncManager(test_config)
        with patch("src.sync_manager.Database", return_value=mock_db):
            with pytest.raises(Exception, match="No encrypted tokens"):
                await manager.initialize(user_id=42)

    @pytest.mark.asyncio
    async def test_initialize_stores_user_id(self, test_config, mock_db, mock_garmin_client):
        """initialize() without user_id uses legacy mode and sets user_id."""
        mock_db.get_encrypted_tokens = AsyncMock(return_value=None)

        manager = SyncManager(test_config)
        with (
            patch("src.sync_manager.Database", return_value=mock_db),
            patch("src.sync_manager.GarminClient", return_value=mock_garmin_client),
        ):
            await manager.initialize(user_id=None)
            assert manager.user_id == 67

    @pytest.mark.asyncio
    async def test_initialize_connects_to_db(self, test_config, mock_db, mock_garmin_client):
        """initialize() connects the database."""
        manager = SyncManager(test_config)
        with (
            patch("src.sync_manager.Database", return_value=mock_db),
            patch("src.sync_manager.GarminClient", return_value=mock_garmin_client),
        ):
            await manager.initialize(user_id=None)
            mock_db.connect.assert_called_once()


# ---------------------------------------------------------------------------
# SyncManager.sync() category filtering tests
# ---------------------------------------------------------------------------


class TestSyncManagerCategoryFiltering:
    """Tests for category selection during sync orchestration."""

    @pytest.mark.asyncio
    async def test_sync_only_specified_categories(
        self, test_config, mock_db, mock_garmin_client
    ):
        """Sync calls fetcher only for the specified categories."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67

        fetch_calls = []

        async def fake_fetch(mode, days_back, start_date, end_date):
            fetch_calls.append(mode)
            return (10, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=fake_fetch)

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["daily_health"])

        assert "daily_health" in report["categories"]
        assert "activities" not in report["categories"]

    @pytest.mark.asyncio
    async def test_sync_all_configured_categories_by_default(
        self, test_config, mock_db, mock_garmin_client
    ):
        """Sync without explicit categories uses config.sync.categories."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(5, None))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync()

        # Config has ["daily_health", "activities"]
        assert "daily_health" in report["categories"]
        assert "activities" in report["categories"]

    @pytest.mark.asyncio
    async def test_sync_unknown_category_raises_value_error(
        self, test_config, mock_db
    ):
        """_get_fetcher raises ValueError for unknown categories."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = MagicMock()
        manager.user_id = 67

        with pytest.raises(ValueError, match="Unknown category"):
            manager._get_fetcher("unknown_category")


# ---------------------------------------------------------------------------
# SyncManager error handling tests
# ---------------------------------------------------------------------------


class TestSyncManagerErrorHandling:
    """Tests for partial failure and error handling during sync."""

    @pytest.mark.asyncio
    async def test_sync_partial_failure_continues_other_categories(
        self, test_config, mock_db, mock_garmin_client
    ):
        """A failing category does not abort other categories."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67

        call_count = 0

        async def fake_fetch(mode, days_back, start_date, end_date):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated fetcher failure")
            return (10, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=fake_fetch)

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["daily_health", "activities"])

        # Both categories must be reported
        assert "daily_health" in report["categories"]
        assert "activities" in report["categories"]
        # First category failed
        assert report["categories"]["daily_health"]["status"] == "failed"
        # Second category succeeded
        assert report["categories"]["activities"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_sync_error_aggregated_in_report(
        self, test_config, mock_db, mock_garmin_client
    ):
        """Errors from failed categories are collected in report['errors']."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=RuntimeError("Network error"))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["daily_health"])

        assert len(report["errors"]) >= 1
        assert "daily_health" in report["errors"][0]

    @pytest.mark.asyncio
    async def test_sync_not_initialized_raises_runtime_error(self, test_config):
        """Calling sync() before initialize() raises RuntimeError."""
        manager = SyncManager(test_config)
        with pytest.raises(RuntimeError, match="not initialized"):
            await manager.sync()

    @pytest.mark.asyncio
    async def test_sync_partial_error_included_in_category_report(
        self, test_config, mock_db, mock_garmin_client
    ):
        """Fetcher returning (records, error_msg) marks category as partial."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(5, "Partial timeout error"))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["activities"])

        cat_report = report["categories"]["activities"]
        assert cat_report["status"] == "partial"
        assert cat_report["records"] == 5
        assert "Partial timeout error" in cat_report["error"]


# ---------------------------------------------------------------------------
# SyncManager dry-run tests
# ---------------------------------------------------------------------------


class TestSyncManagerDryRun:
    """Tests for dry-run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_date_ranges(
        self, test_config, mock_db, mock_garmin_client
    ):
        """Dry run returns date range info without writing data."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67

        mock_fetcher = MagicMock()
        mock_fetcher.determine_date_range = AsyncMock(
            return_value=(date(2024, 1, 1), date(2024, 1, 31))
        )

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(
                categories=["daily_health"], dry_run=True
            )

        assert report.get("dry_run") is True
        assert "daily_health" in report["categories"]
        cat = report["categories"]["daily_health"]
        assert "start_date" in cat
        assert "end_date" in cat

    @pytest.mark.asyncio
    async def test_dry_run_does_not_call_fetch(
        self, test_config, mock_db, mock_garmin_client
    ):
        """Dry run never calls fetcher.fetch()."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock()
        mock_fetcher.determine_date_range = AsyncMock(
            return_value=(date(2024, 1, 1), date(2024, 1, 31))
        )

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            await manager.sync(categories=["activities"], dry_run=True)

        mock_fetcher.fetch.assert_not_called()


# ---------------------------------------------------------------------------
# SyncManager cleanup tests
# ---------------------------------------------------------------------------


class TestSyncManagerCleanup:
    """Tests for SyncManager.cleanup() behavior."""

    @pytest.mark.asyncio
    async def test_cleanup_disconnects_db(self, test_config, mock_db):
        """cleanup() always disconnects the DB."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = None
        manager._tokens_from_db = False

        await manager.cleanup()
        mock_db.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_re_encrypts_tokens_when_from_db(
        self, test_config, mock_db, mock_garmin_client, token_key
    ):
        """cleanup() stores refreshed tokens when loaded from DB."""
        os.environ["GARMIN_TOKEN_KEY"] = token_key

        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 67
        manager._tokens_from_db = True

        # mock_garmin_client.get_refreshed_tokens returns b"fresh-tokens"
        with patch("src.token_manager.TokenManager") as MockTM:
            mock_tm_instance = MagicMock()
            mock_tm_instance.encrypt = MagicMock(return_value=b"encrypted-fresh")
            MockTM.return_value = mock_tm_instance
            await manager.cleanup()

        mock_db.store_encrypted_tokens.assert_called_once()
