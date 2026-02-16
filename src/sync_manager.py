"""Sync manager for orchestrating data synchronization."""

import logging
from datetime import date
from typing import Optional, Dict, Any, List

from .config import Config
from .database import Database
from .garmin_client import GarminClient
from .fetchers.daily_health import DailyHealthFetcher
from .fetchers.activities import ActivitiesFetcher
from .fetchers.body_comp import BodyCompositionFetcher
from .fetchers.advanced_metrics import AdvancedMetricsFetcher
from .fetchers.wellness import WellnessFetcher

logger = logging.getLogger(__name__)


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

    async def initialize(self) -> None:
        """Initialize database and Garmin connections."""
        logger.info("Initializing sync manager...")

        # Initialize database
        self.db = Database(self.config.database)
        await self.db.connect()

        # Initialize Garmin client
        self.garmin_client = GarminClient(
            self.config.garmin,
            rate_limit_delay=self.config.sync.rate_limit_delay,
        )
        self.garmin_client.connect()

        # Get or create user
        success, profile, error = self.garmin_client.get_user_profile()
        if not success:
            raise Exception(f"Failed to get user profile: {error}")

        # Extract user info - get_full_name() returns a string or dict
        if isinstance(profile, dict):
            garmin_user_id = str(profile.get("userId") or profile.get("displayName") or "unknown")
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
        """Clean up connections."""
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
        """Perform synchronization.

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

        # Use provided values or defaults from config
        categories = categories or self.config.sync.categories
        mode = mode or self.config.sync.mode
        days_back = days_back or self.config.sync.days_back

        logger.info(f"Starting sync - Mode: {mode}, Categories: {categories}")

        if dry_run:
            logger.info("DRY RUN MODE - No data will be written")
            return await self._dry_run_sync(categories, mode, days_back, start_date, end_date)

        # Perform actual sync
        report = {
            "mode": mode,
            "categories": {},
            "total_records": 0,
            "errors": [],
        }

        for category in categories:
            logger.info(f"Syncing category: {category}")

            try:
                records, error = await self._sync_category(
                    category, mode, days_back, start_date, end_date
                )

                report["categories"][category] = {
                    "records": records,
                    "status": "success" if error is None else "partial",
                    "error": error,
                }
                report["total_records"] += records

                if error:
                    report["errors"].append(f"{category}: {error}")

            except Exception as e:
                error_msg = f"Failed to sync {category}: {e}"
                logger.exception(error_msg)
                report["categories"][category] = {
                    "records": 0,
                    "status": "failed",
                    "error": str(e),
                }
                report["errors"].append(error_msg)

        logger.info(f"Sync complete - Total records: {report['total_records']}")
        return report

    async def _sync_category(
        self,
        category: str,
        mode: str,
        days_back: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> tuple[int, Optional[str]]:
        """Sync a specific category.

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
