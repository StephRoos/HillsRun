"""Sync manager for orchestrating data synchronization."""

import asyncio
import logging
import os
import time
from datetime import date
from typing import Optional, Dict, Any, List

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import asyncpg

from .config import Config
from .database import Database
from .garmin_client import GarminClient
from .fetchers.daily_health import DailyHealthFetcher
from .fetchers.activities import ActivitiesFetcher
from .fetchers.body_comp import BodyCompositionFetcher
from .fetchers.advanced_metrics import AdvancedMetricsFetcher
from .fetchers.wellness import WellnessFetcher

logger = logging.getLogger(__name__)

# Per-user locks to prevent concurrent syncs for the same user
_user_locks: Dict[int, asyncio.Lock] = {}
_user_locks_guard = asyncio.Lock()

# Transient exceptions worth retrying at the category level
_CATEGORY_RETRYABLE = (
    ConnectionError,
    TimeoutError,
    asyncpg.PostgresConnectionError,
    asyncpg.InterfaceError,
    asyncio.TimeoutError,
)

# Category sync timeout (seconds)
CATEGORY_SYNC_TIMEOUT = 300


async def _get_user_lock(user_id: int) -> asyncio.Lock:
    """Get or create an asyncio.Lock for a specific user.

    Args:
        user_id: User ID to get lock for

    Returns:
        asyncio.Lock for the user
    """
    async with _user_locks_guard:
        if user_id not in _user_locks:
            _user_locks[user_id] = asyncio.Lock()
        return _user_locks[user_id]


class SyncManager:
    """Manages synchronization of Garmin Connect data to PostgreSQL."""

    def __init__(self, config: Config):
        """Initialize sync manager.

        Args:
            config: Application configuration
        """
        self.config = config
        self.db: Optional[Database] = None
        self.garmin_client: Optional[GarminClient] = None
        self.user_id: Optional[int] = None
        self._tokens_from_db = False

    async def initialize(self, user_id: Optional[int] = None) -> None:
        """Initialize database and Garmin connections.

        Args:
            user_id: Optional specific user_id to sync for (loads tokens from DB).
                     If None, uses filesystem tokens (backward compat).
        """
        logger.info("Initializing sync manager...")

        # Initialize database
        self.db = Database(self.config.database)
        await self.db.connect()

        if user_id is not None:
            # Per-user mode: load tokens from DB
            encrypted_tokens = await self.db.get_encrypted_tokens(user_id)
            if not encrypted_tokens:
                raise Exception(f"No encrypted tokens found for user_id={user_id}")

            token_key = os.environ.get("GARMIN_TOKEN_KEY", "")
            if not token_key:
                raise Exception("GARMIN_TOKEN_KEY environment variable is required")

            self.garmin_client = GarminClient.from_encrypted_tokens(
                encrypted_tokens,
                token_key,
                rate_limit_delay=self.config.sync.rate_limit_delay,
            )
            self.user_id = user_id
            self._tokens_from_db = True
            logger.info(f"Initialized for user_id={user_id} (tokens from DB)")
        else:
            # Legacy mode: filesystem tokens
            self.garmin_client = GarminClient(
                self.config.garmin,
                rate_limit_delay=self.config.sync.rate_limit_delay,
            )
            self.garmin_client.connect()

            # Get or create user
            success, profile, error = self.garmin_client.get_user_profile()
            if not success:
                raise Exception(f"Failed to get user profile: {error}")

            if isinstance(profile, dict):
                garmin_user_id = str(
                    profile.get("userId") or profile.get("displayName") or "unknown"
                )
                display_name = profile.get("displayName")
            else:
                garmin_user_id = str(profile) if profile else "unknown"
                display_name = str(profile) if profile else None

            self.user_id = await self.db.get_or_create_user(
                garmin_user_id=garmin_user_id,
                display_name=display_name,
            )
            logger.info(f"Initialized for user: {display_name} (ID: {self.user_id})")

    async def cleanup(self) -> None:
        """Clean up connections. Re-encrypt refreshed tokens if loaded from DB."""
        if self._tokens_from_db and self.garmin_client and self.db and self.user_id:
            try:
                from .token_manager import TokenManager

                token_key = os.environ.get("GARMIN_TOKEN_KEY", "")
                refreshed = self.garmin_client.get_refreshed_tokens()
                tm = TokenManager(token_key)
                encrypted = tm.encrypt(refreshed)
                await self.db.store_encrypted_tokens(self.user_id, encrypted)
                logger.info(f"Re-encrypted refreshed tokens for user_id={self.user_id}")
            except Exception as e:
                logger.warning(f"Failed to re-encrypt tokens: {e}")
        if self.db:
            await self.db.disconnect()
        logger.info("Sync manager cleanup complete")

    async def sync(
        self,
        categories: Optional[List[str]] = None,
        mode: Optional[str] = None,
        days_back: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Perform synchronization with per-user locking.

        Acquires an async lock per user_id to prevent concurrent syncs
        for the same user. Each category is synced with retry + timeout.

        Args:
            categories: Optional list of categories to sync (defaults to config)
            mode: Optional sync mode override ('incremental' or 'full')
            days_back: Optional days_back override
            start_date: Optional start date override
            end_date: Optional end date override
            dry_run: If True, show what would be synced without syncing

        Returns:
            Sync report dictionary
        """
        if not self.db or not self.garmin_client or not self.user_id:
            raise RuntimeError("Sync manager not initialized. Call initialize() first.")

        # Acquire per-user lock to prevent concurrent syncs
        lock = await _get_user_lock(self.user_id)
        if lock.locked():
            raise RuntimeError(
                f"Sync already in progress for user_id={self.user_id}"
            )

        async with lock:
            return await self._sync_locked(
                categories, mode, days_back, start_date, end_date, dry_run
            )

    async def _sync_locked(
        self,
        categories: Optional[List[str]],
        mode: Optional[str],
        days_back: Optional[int],
        start_date: Optional[date],
        end_date: Optional[date],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Internal sync logic, called while holding the per-user lock."""
        categories = categories or self.config.sync.categories
        mode = mode or self.config.sync.mode
        days_back = days_back or self.config.sync.days_back

        logger.info(
            f"[user={self.user_id}] Starting sync - Mode: {mode}, Categories: {categories}"
        )
        sync_start = time.monotonic()

        if dry_run:
            logger.info(f"[user={self.user_id}] DRY RUN MODE - No data will be written")
            return await self._dry_run_sync(
                categories, mode, days_back, start_date, end_date
            )

        report = {
            "mode": mode,
            "categories": {},
            "total_records": 0,
            "errors": [],
        }

        for category in categories:
            cat_start = time.monotonic()
            logger.info(f"[user={self.user_id}] Syncing category: {category}")

            try:
                # Wrap category sync in a timeout
                records, error = await asyncio.wait_for(
                    self._sync_category_with_retry(
                        category, mode, days_back, start_date, end_date
                    ),
                    timeout=CATEGORY_SYNC_TIMEOUT,
                )

                cat_duration = time.monotonic() - cat_start
                report["categories"][category] = {
                    "records": records,
                    "status": "success" if error is None else "partial",
                    "error": error,
                    "duration_seconds": round(cat_duration, 1),
                }
                report["total_records"] += records

                if error:
                    report["errors"].append(f"{category}: {error}")

                logger.info(
                    f"[user={self.user_id}] {category}: {records} records in {cat_duration:.1f}s"
                )

            except asyncio.TimeoutError:
                cat_duration = time.monotonic() - cat_start
                error_msg = f"{category}: timed out after {CATEGORY_SYNC_TIMEOUT}s"
                logger.error(f"[user={self.user_id}] {error_msg}")
                report["categories"][category] = {
                    "records": 0,
                    "status": "failed",
                    "error": error_msg,
                    "duration_seconds": round(cat_duration, 1),
                }
                report["errors"].append(error_msg)

            except Exception as e:
                cat_duration = time.monotonic() - cat_start
                error_msg = f"Failed to sync {category}: {e}"
                logger.exception(f"[user={self.user_id}] {error_msg}")
                report["categories"][category] = {
                    "records": 0,
                    "status": "failed",
                    "error": str(e),
                    "duration_seconds": round(cat_duration, 1),
                }
                report["errors"].append(error_msg)

        total_duration = time.monotonic() - sync_start
        report["duration_seconds"] = round(total_duration, 1)
        logger.info(
            f"[user={self.user_id}] Sync complete - "
            f"{report['total_records']} records in {total_duration:.1f}s"
        )
        return report

    async def _sync_category_with_retry(
        self,
        category: str,
        mode: str,
        days_back: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> tuple[int, Optional[str]]:
        """Sync a category with tenacity retry on transient errors.

        Retries up to 3 times with exponential backoff (2s → 30s)
        on connection/timeout errors.

        Args:
            category: Category name
            mode: Sync mode
            days_back: Days to go back
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Tuple of (records_count, error_message)
        """
        # Build retry decorator dynamically so it's testable
        retrying = retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(min=2, max=30),
            retry=retry_if_exception_type(_CATEGORY_RETRYABLE),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        @retrying
        async def _do_sync():
            fetcher = self._get_fetcher(category)
            return await fetcher.fetch(mode, days_back, start_date, end_date)

        return await _do_sync()

    async def _sync_category(
        self,
        category: str,
        mode: str,
        days_back: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> tuple[int, Optional[str]]:
        """Sync a specific category (no retry, for backward compat).

        Args:
            category: Category name
            mode: Sync mode
            days_back: Days to go back
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Tuple of (records_count, error_message)
        """
        fetcher = self._get_fetcher(category)
        return await fetcher.fetch(mode, days_back, start_date, end_date)

    def _get_fetcher(self, category: str):
        """Get appropriate fetcher for category.

        Args:
            category: Category name

        Returns:
            Fetcher instance

        Raises:
            ValueError: If category is unknown
        """
        fetcher_map = {
            "daily_health": DailyHealthFetcher,
            "activities": ActivitiesFetcher,
            "body_composition": BodyCompositionFetcher,
            "advanced_metrics": AdvancedMetricsFetcher,
            "wellness": WellnessFetcher,
        }

        fetcher_class = fetcher_map.get(category)
        if not fetcher_class:
            raise ValueError(f"Unknown category: {category}")

        return fetcher_class(
            db=self.db,
            garmin_client=self.garmin_client,
            user_id=self.user_id,
            category=category,
        )

    async def _dry_run_sync(
        self,
        categories: List[str],
        mode: str,
        days_back: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> Dict[str, Any]:
        """Perform dry run to show what would be synced.

        Args:
            categories: Categories to sync
            mode: Sync mode
            days_back: Days to go back
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dry run report
        """
        report = {
            "mode": mode,
            "dry_run": True,
            "categories": {},
        }

        for category in categories:
            fetcher = self._get_fetcher(category)
            start, end = await fetcher.determine_date_range(
                mode, days_back, start_date, end_date
            )

            report["categories"][category] = {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "days": (end - start).days + 1,
            }

            logger.info(
                f"[DRY RUN] {category}: Would sync from {start} to {end} ({(end - start).days + 1} days)"
            )

        return report
