"""Unit tests for SyncManager orchestration logic."""

import os
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Config, DatabaseConfig, GarminConfig, SyncConfig, LoggingConfig
from src.sync_manager import SyncManager
from src.fetchers.daily_health import DailyHealthFetcher
from src.fetchers.activities import ActivitiesFetcher
from src.fetchers.body_comp import BodyCompositionFetcher
from src.fetchers.advanced_metrics import AdvancedMetricsFetcher
from src.fetchers.wellness import WellnessFetcher
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
    """Config instance suitable for unit tests."""
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
        sync=SyncConfig(
            categories=["daily_health", "activities", "body_composition"]
        ),
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
    db.get_or_create_user = AsyncMock(return_value=42)
    db.query_sync_status = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_garmin_client():
    """Mocked GarminClient."""
    client = MagicMock()
    client.connect = MagicMock()
    client.get_user_profile = MagicMock(
        return_value=(True, {"userId": "12345", "displayName": "Test Runner"}, None)
    )
    client.get_refreshed_tokens = MagicMock(return_value=b"fresh-tokens")
    return client


@pytest.fixture
def initialized_manager(test_config, mock_db, mock_garmin_client):
    """SyncManager pre-initialized (db + garmin_client + user_id set directly)."""
    manager = SyncManager(test_config)
    manager.db = mock_db
    manager.garmin_client = mock_garmin_client
    manager.user_id = 42
    return manager


# ---------------------------------------------------------------------------
# _get_fetcher() tests
# ---------------------------------------------------------------------------


class TestGetFetcher:
    """Tests for SyncManager._get_fetcher()."""

    def test_get_fetcher_daily_health_returns_correct_class(
        self, initialized_manager
    ):
        """_get_fetcher('daily_health') returns DailyHealthFetcher instance."""
        fetcher = initialized_manager._get_fetcher("daily_health")
        assert isinstance(fetcher, DailyHealthFetcher)

    def test_get_fetcher_activities_returns_correct_class(
        self, initialized_manager
    ):
        """_get_fetcher('activities') returns ActivitiesFetcher instance."""
        fetcher = initialized_manager._get_fetcher("activities")
        assert isinstance(fetcher, ActivitiesFetcher)

    def test_get_fetcher_body_composition_returns_correct_class(
        self, initialized_manager
    ):
        """_get_fetcher('body_composition') returns BodyCompositionFetcher instance."""
        fetcher = initialized_manager._get_fetcher("body_composition")
        assert isinstance(fetcher, BodyCompositionFetcher)

    def test_get_fetcher_advanced_metrics_returns_correct_class(
        self, initialized_manager
    ):
        """_get_fetcher('advanced_metrics') returns AdvancedMetricsFetcher instance."""
        fetcher = initialized_manager._get_fetcher("advanced_metrics")
        assert isinstance(fetcher, AdvancedMetricsFetcher)

    def test_get_fetcher_wellness_returns_correct_class(
        self, initialized_manager
    ):
        """_get_fetcher('wellness') returns WellnessFetcher instance."""
        fetcher = initialized_manager._get_fetcher("wellness")
        assert isinstance(fetcher, WellnessFetcher)

    def test_get_fetcher_unknown_category_raises_value_error(
        self, initialized_manager
    ):
        """_get_fetcher raises ValueError for an unknown category name."""
        with pytest.raises(ValueError, match="Unknown category"):
            initialized_manager._get_fetcher("unknown_category")

    def test_get_fetcher_empty_string_raises_value_error(
        self, initialized_manager
    ):
        """_get_fetcher raises ValueError for an empty string category."""
        with pytest.raises(ValueError, match="Unknown category"):
            initialized_manager._get_fetcher("")

    def test_get_fetcher_injects_db_and_user_id(self, initialized_manager):
        """Returned fetcher has the correct db and user_id attributes."""
        fetcher = initialized_manager._get_fetcher("activities")
        assert fetcher.db is initialized_manager.db
        assert fetcher.user_id == initialized_manager.user_id
        assert fetcher.garmin_client is initialized_manager.garmin_client


# ---------------------------------------------------------------------------
# sync() category selection tests
# ---------------------------------------------------------------------------


class TestSyncCategorySelection:
    """Tests for sync() category filtering behaviour."""

    @pytest.mark.asyncio
    async def test_sync_with_explicit_categories_only_runs_those(
        self, initialized_manager
    ):
        """sync(categories=['daily_health']) does not run other categories."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(5, None))

        with patch.object(initialized_manager, "_get_fetcher", return_value=mock_fetcher):
            report = await initialized_manager.sync(categories=["daily_health"])

        assert "daily_health" in report["categories"]
        assert "activities" not in report["categories"]
        assert "body_composition" not in report["categories"]

    @pytest.mark.asyncio
    async def test_sync_without_categories_uses_config_defaults(
        self, initialized_manager
    ):
        """sync() with no categories argument falls back to config.sync.categories."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(3, None))

        with patch.object(initialized_manager, "_get_fetcher", return_value=mock_fetcher):
            report = await initialized_manager.sync()

        # Config categories: ["daily_health", "activities", "body_composition"]
        assert "daily_health" in report["categories"]
        assert "activities" in report["categories"]
        assert "body_composition" in report["categories"]

    @pytest.mark.asyncio
    async def test_sync_calls_fetcher_for_each_specified_category(
        self, initialized_manager
    ):
        """sync() calls _get_fetcher once for each requested category."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(1, None))

        categories = ["daily_health", "activities"]
        get_fetcher_calls = []

        def track_get_fetcher(category):
            get_fetcher_calls.append(category)
            return mock_fetcher

        with patch.object(initialized_manager, "_get_fetcher", side_effect=track_get_fetcher):
            await initialized_manager.sync(categories=categories)

        assert get_fetcher_calls == categories

    @pytest.mark.asyncio
    async def test_sync_single_category_produces_correct_report_keys(
        self, initialized_manager
    ):
        """sync() report has expected top-level structure."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(7, None))

        with patch.object(initialized_manager, "_get_fetcher", return_value=mock_fetcher):
            report = await initialized_manager.sync(categories=["wellness"])

        assert "mode" in report
        assert "categories" in report
        assert "total_records" in report
        assert "errors" in report

    @pytest.mark.asyncio
    async def test_sync_total_records_sums_across_categories(
        self, initialized_manager
    ):
        """total_records in report is the sum of all category records."""
        call_index = 0

        async def fetch_varying(*args, **kwargs):
            nonlocal call_index
            call_index += 1
            return (call_index * 10, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=fetch_varying)

        with patch.object(initialized_manager, "_get_fetcher", return_value=mock_fetcher):
            report = await initialized_manager.sync(
                categories=["daily_health", "activities"]
            )

        # First category: 10 records, second: 20 records → total = 30
        assert report["total_records"] == 30


# ---------------------------------------------------------------------------
# sync() dry_run tests
# ---------------------------------------------------------------------------


class TestSyncDryRun:
    """Tests for sync() dry_run=True behaviour."""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_call_fetch(self, initialized_manager):
        """dry_run=True never calls fetcher.fetch()."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock()
        mock_fetcher.determine_date_range = AsyncMock(
            return_value=(date(2024, 1, 1), date(2024, 1, 31))
        )

        with patch.object(initialized_manager, "_get_fetcher", return_value=mock_fetcher):
            await initialized_manager.sync(categories=["daily_health"], dry_run=True)

        mock_fetcher.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_flag_set_in_report(self, initialized_manager):
        """dry_run report includes dry_run=True flag."""
        mock_fetcher = MagicMock()
        mock_fetcher.determine_date_range = AsyncMock(
            return_value=(date(2024, 1, 1), date(2024, 1, 31))
        )

        with patch.object(initialized_manager, "_get_fetcher", return_value=mock_fetcher):
            report = await initialized_manager.sync(
                categories=["activities"], dry_run=True
            )

        assert report.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_calls_determine_date_range(self, initialized_manager):
        """dry_run calls determine_date_range on the fetcher."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock()
        mock_fetcher.determine_date_range = AsyncMock(
            return_value=(date(2024, 3, 1), date(2024, 3, 31))
        )

        with patch.object(initialized_manager, "_get_fetcher", return_value=mock_fetcher):
            report = await initialized_manager.sync(
                categories=["daily_health"], dry_run=True
            )

        mock_fetcher.determine_date_range.assert_called_once()
        cat = report["categories"]["daily_health"]
        assert cat["start_date"] == "2024-03-01"
        assert cat["end_date"] == "2024-03-31"


# ---------------------------------------------------------------------------
# cleanup() token re-encryption tests
# ---------------------------------------------------------------------------


class TestSyncManagerCleanupTokens:
    """Tests for cleanup() token re-encryption when tokens were loaded from DB."""

    @pytest.mark.asyncio
    async def test_cleanup_re_encrypts_tokens_when_loaded_from_db(
        self, test_config, mock_db, mock_garmin_client, token_key
    ):
        """cleanup() stores re-encrypted refreshed tokens when _tokens_from_db=True."""
        os.environ["GARMIN_TOKEN_KEY"] = token_key

        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 42
        manager._tokens_from_db = True

        with patch("src.token_manager.TokenManager") as MockTM:
            mock_tm_instance = MagicMock()
            mock_tm_instance.encrypt = MagicMock(return_value=b"re-encrypted-tokens")
            MockTM.return_value = mock_tm_instance
            await manager.cleanup()

        mock_db.store_encrypted_tokens.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_does_not_re_encrypt_when_not_from_db(
        self, test_config, mock_db, mock_garmin_client
    ):
        """cleanup() skips token re-encryption when _tokens_from_db=False."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager.user_id = 42
        manager._tokens_from_db = False

        await manager.cleanup()

        mock_db.store_encrypted_tokens.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_always_disconnects_db(
        self, test_config, mock_db, mock_garmin_client
    ):
        """cleanup() calls db.disconnect() regardless of token source."""
        manager = SyncManager(test_config)
        manager.db = mock_db
        manager.garmin_client = mock_garmin_client
        manager._tokens_from_db = False

        await manager.cleanup()

        mock_db.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_without_db_does_not_raise(self, test_config):
        """cleanup() with no db set completes without error."""
        manager = SyncManager(test_config)
        manager.db = None
        manager.garmin_client = None
        manager._tokens_from_db = False

        # Should not raise
        await manager.cleanup()
