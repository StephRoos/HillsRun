"""Tests for sync robustness: retry, lock, timeout, error handling."""

import asyncio
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Config, DatabaseConfig, GarminConfig, SyncConfig, LoggingConfig
from src.sync_manager import (
    SyncManager,
    _get_user_lock,
    _user_locks,
    CATEGORY_SYNC_TIMEOUT,
)
from src.token_manager import TokenManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def token_key():
    return TokenManager.generate_key()


@pytest.fixture
def test_config(tmp_path, token_key):
    return Config(
        database=DatabaseConfig(
            host="localhost", port=5432, database="test_garmin",
            user="test_user", password="test_pass",
        ),
        garmin=GarminConfig(
            tokens_dir=tmp_path / "tokens", email="t@t.com",
            password="p", token_key=token_key,
        ),
        sync=SyncConfig(categories=["daily_health", "activities"]),
        logging=LoggingConfig(),
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    return db


@pytest.fixture
def mock_garmin_client():
    client = MagicMock()
    client.get_refreshed_tokens = MagicMock(return_value=b"tokens")
    return client


@pytest.fixture
def manager(test_config, mock_db, mock_garmin_client):
    """Pre-initialized SyncManager."""
    m = SyncManager(test_config)
    m.db = mock_db
    m.garmin_client = mock_garmin_client
    m.user_id = 42
    return m


@pytest.fixture(autouse=True)
def clear_locks():
    """Clear user locks between tests to avoid interference."""
    _user_locks.clear()
    yield
    _user_locks.clear()


# ---------------------------------------------------------------------------
# Per-user lock tests
# ---------------------------------------------------------------------------


class TestSyncLock:
    """Tests for per-user sync lock preventing concurrent syncs."""

    @pytest.mark.asyncio
    async def test_get_user_lock_creates_lock_for_new_user(self):
        """_get_user_lock creates a new lock for an unseen user_id."""
        lock = await _get_user_lock(99)
        assert isinstance(lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_get_user_lock_returns_same_lock_for_same_user(self):
        """_get_user_lock returns the same lock instance for the same user."""
        lock1 = await _get_user_lock(42)
        lock2 = await _get_user_lock(42)
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_different_users_get_different_locks(self):
        """Different user_ids get distinct lock instances."""
        lock_a = await _get_user_lock(1)
        lock_b = await _get_user_lock(2)
        assert lock_a is not lock_b

    @pytest.mark.asyncio
    async def test_concurrent_sync_raises_when_lock_held(self, manager):
        """sync() raises RuntimeError if the user lock is already held."""
        lock = await _get_user_lock(manager.user_id)

        # Simulate a running sync by holding the lock
        async with lock:
            with pytest.raises(RuntimeError, match="Sync already in progress"):
                await manager.sync(categories=["daily_health"])

    @pytest.mark.asyncio
    async def test_sync_releases_lock_after_completion(self, manager):
        """Lock is released after sync completes successfully."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(5, None))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            await manager.sync(categories=["daily_health"])

        lock = await _get_user_lock(manager.user_id)
        assert not lock.locked()

    @pytest.mark.asyncio
    async def test_sync_releases_lock_after_error(self, manager):
        """Lock is released even if sync fails with an exception."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=RuntimeError("boom"))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            # sync catches the exception and reports it, doesn't re-raise
            report = await manager.sync(categories=["daily_health"])

        lock = await _get_user_lock(manager.user_id)
        assert not lock.locked()
        assert report["categories"]["daily_health"]["status"] == "failed"


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------


class TestSyncRetry:
    """Tests for tenacity retry logic on category sync."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, manager):
        """Category sync retries on ConnectionError and succeeds."""
        call_count = 0

        async def flaky_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("DB connection lost")
            return (10, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=flaky_fetch)

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            records, error = await manager._sync_category_with_retry(
                "daily_health", "incremental", 7, None, None
            )

        assert records == 10
        assert error is None
        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self, manager):
        """Category sync retries on TimeoutError."""
        call_count = 0

        async def flaky_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("timed out")
            return (5, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=flaky_fetch)

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            records, error = await manager._sync_category_with_retry(
                "daily_health", "incremental", 7, None, None
            )

        assert records == 5
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_value_error(self, manager):
        """Non-retryable errors are not retried."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=ValueError("bad data"))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            with pytest.raises(ValueError, match="bad data"):
                await manager._sync_category_with_retry(
                    "daily_health", "incremental", 7, None, None
                )

        # Should only be called once (no retry)
        assert mock_fetcher.fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, manager):
        """After 3 retries, the original exception is re-raised."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(
            side_effect=ConnectionError("persistent failure")
        )

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            with pytest.raises(ConnectionError, match="persistent failure"):
                await manager._sync_category_with_retry(
                    "daily_health", "incremental", 7, None, None
                )

        assert mock_fetcher.fetch.call_count == 3


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------


class TestSyncTimeout:
    """Tests for category sync timeout."""

    @pytest.mark.asyncio
    async def test_timeout_reported_as_failed(self, manager):
        """A category that times out is reported as failed."""
        async def slow_fetch(*args, **kwargs):
            await asyncio.sleep(10)
            return (0, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=slow_fetch)

        # Patch CATEGORY_SYNC_TIMEOUT to a tiny value for testing
        with (
            patch.object(manager, "_get_fetcher", return_value=mock_fetcher),
            patch("src.sync_manager.CATEGORY_SYNC_TIMEOUT", 0.1),
        ):
            report = await manager.sync(categories=["daily_health"])

        cat = report["categories"]["daily_health"]
        assert cat["status"] == "failed"
        assert "timed out" in cat["error"]

    @pytest.mark.asyncio
    async def test_timeout_does_not_block_other_categories(self, manager):
        """A timed-out category doesn't prevent other categories from syncing."""
        call_count = 0

        async def conditional_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                await asyncio.sleep(10)  # Will timeout
            return (5, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=conditional_fetch)

        with (
            patch.object(manager, "_get_fetcher", return_value=mock_fetcher),
            patch("src.sync_manager.CATEGORY_SYNC_TIMEOUT", 0.1),
        ):
            report = await manager.sync(
                categories=["daily_health", "activities"]
            )

        assert report["categories"]["daily_health"]["status"] == "failed"
        assert report["categories"]["activities"]["status"] == "success"
        assert report["categories"]["activities"]["records"] == 5


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestSyncErrorHandling:
    """Tests for error handling: Garmin API down, DB down, etc."""

    @pytest.mark.asyncio
    async def test_garmin_api_failure_captured_in_report(self, manager):
        """Garmin API error is captured and doesn't crash the sync."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(
            side_effect=RuntimeError("Garmin API unreachable")
        )

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["daily_health"])

        cat = report["categories"]["daily_health"]
        assert cat["status"] == "failed"
        assert "Garmin API unreachable" in cat["error"]
        assert len(report["errors"]) == 1

    @pytest.mark.asyncio
    async def test_partial_error_from_fetcher(self, manager):
        """Fetcher returning partial error marks category as partial."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(
            return_value=(8, "Some dates failed")
        )

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["activities"])

        cat = report["categories"]["activities"]
        assert cat["status"] == "partial"
        assert cat["records"] == 8

    @pytest.mark.asyncio
    async def test_all_categories_fail_report_still_returned(self, manager):
        """Even when all categories fail, a valid report is returned."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=RuntimeError("total failure"))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(
                categories=["daily_health", "activities"]
            )

        assert report["total_records"] == 0
        assert len(report["errors"]) == 2
        assert report["categories"]["daily_health"]["status"] == "failed"
        assert report["categories"]["activities"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_report_includes_duration(self, manager):
        """Report includes duration_seconds at top and category level."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=(3, None))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["daily_health"])

        assert "duration_seconds" in report
        assert "duration_seconds" in report["categories"]["daily_health"]
        assert isinstance(report["duration_seconds"], float)

    @pytest.mark.asyncio
    async def test_not_initialized_raises(self, test_config):
        """sync() before initialize() raises RuntimeError."""
        m = SyncManager(test_config)
        with pytest.raises(RuntimeError, match="not initialized"):
            await m.sync()


# ---------------------------------------------------------------------------
# Sync failure persistence tests
# ---------------------------------------------------------------------------


class TestSyncFailurePersistence:
    """Tests for _record_sync_failure persisting errors to DB sync_state."""

    @pytest.mark.asyncio
    async def test_exception_records_failure_in_db(self, manager, mock_db):
        """When a category raises, sync_state is updated with 'failed' status."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=RuntimeError("Garmin down"))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["daily_health"])

        # Verify DB was called to record the failure
        mock_db.update_sync_state.assert_called_once()
        call_kwargs = mock_db.update_sync_state.call_args
        assert call_kwargs.kwargs["category"] == "daily_health"
        assert call_kwargs.kwargs["sync_status"] == "failed"
        assert "Garmin down" in call_kwargs.kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_timeout_records_failure_in_db(self, manager, mock_db):
        """When a category times out, sync_state is updated with 'failed' status."""
        async def slow_fetch(*args, **kwargs):
            await asyncio.sleep(10)
            return (0, None)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=slow_fetch)

        with (
            patch.object(manager, "_get_fetcher", return_value=mock_fetcher),
            patch("src.sync_manager.CATEGORY_SYNC_TIMEOUT", 0.1),
        ):
            report = await manager.sync(categories=["daily_health"])

        mock_db.update_sync_state.assert_called_once()
        call_kwargs = mock_db.update_sync_state.call_args
        assert call_kwargs.kwargs["sync_status"] == "failed"
        assert "timed out" in call_kwargs.kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_record_failure_db_error_does_not_crash(self, manager, mock_db):
        """If recording failure in DB also fails, sync continues gracefully."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=RuntimeError("API error"))
        mock_db.update_sync_state = AsyncMock(side_effect=Exception("DB down too"))

        with patch.object(manager, "_get_fetcher", return_value=mock_fetcher):
            report = await manager.sync(categories=["daily_health", "activities"])

        # Both categories should still be reported
        assert report["categories"]["daily_health"]["status"] == "failed"
        assert report["categories"]["activities"]["status"] == "failed"
