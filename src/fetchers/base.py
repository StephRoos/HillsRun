"""Base fetcher class for all data fetchers."""

import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional, Tuple

from ..database import Database
from ..garmin_client import GarminClient

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Abstract base class for all data fetchers."""

    def __init__(
        self,
        db: Database,
        garmin_client: GarminClient,
        user_id: int,
        category: str,
    ):
        """Initialize fetcher.

        Args:
            db: Database instance
            garmin_client: Garmin client instance
            user_id: User ID in database
            category: Sync category name
        """
        self.db = db
        self.garmin_client = garmin_client
        self.user_id = user_id
        self.category = category

    async def determine_date_range(
        self,
        mode: str,
        days_back: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[date, date]:
        """Determine date range for fetching data.

        Args:
            mode: Sync mode ('incremental' or 'full')
            days_back: Number of days to go back for full sync
            start_date: Optional override start date
            end_date: Optional override end date

        Returns:
            Tuple of (start_date, end_date)
        """
        # If explicit dates provided, use them
        if start_date and end_date:
            return start_date, end_date

        # End date is tomorrow to cover timezone differences (server may be in UTC
        # while Garmin activities use the user's local time)
        end = end_date or (date.today() + timedelta(days=1))

        # Determine start date based on mode
        if mode == "incremental":
            # Get last sync date for this category (per-user if user_id is set)
            last_sync = await self.db.get_last_sync_date(self.category, user_id=self.user_id)

            if last_sync:
                # Start from day after last sync
                start = last_sync + timedelta(days=1)
                logger.info(f"{self.category}: Incremental sync from {start} to {end}")
            else:
                # No previous sync, do full sync
                start = end - timedelta(days=days_back)
                logger.info(
                    f"{self.category}: No previous sync found, doing full sync from {start} to {end}"
                )
        else:  # mode == "full"
            start = end - timedelta(days=days_back)
            logger.info(f"{self.category}: Full sync from {start} to {end}")

        # Ensure start is not after end
        if start > end:
            start = end

        return start, end

    @abstractmethod
    async def fetch(
        self,
        mode: str = "incremental",
        days_back: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[int, Optional[str]]:
        """Fetch and store data.

        Args:
            mode: Sync mode ('incremental' or 'full')
            days_back: Number of days to go back for full sync
            start_date: Optional override start date
            end_date: Optional override end date

        Returns:
            Tuple of (records_count, error_message)
        """
        pass

    async def update_sync_state(
        self,
        last_date: date,
        records_count: int,
        error_message: Optional[str] = None,
    ) -> None:
        """Update sync state after fetch.

        Args:
            last_date: Last successfully synced date
            records_count: Number of records synced
            error_message: Optional error message
        """
        sync_status = "success" if error_message is None else "partial"
        await self.db.update_sync_state(
            category=self.category,
            last_sync_date=last_date,
            records_synced=records_count,
            sync_status=sync_status,
            error_message=error_message,
            user_id=self.user_id,
        )
