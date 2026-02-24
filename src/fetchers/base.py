"""Base fetcher class for all data fetchers."""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Tuple

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

    @staticmethod
    def _ensure_dict(data) -> Optional[Dict[str, Any]]:
        """Ensure data is a dict. If it's a list, take first element."""
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        return None

    @staticmethod
    def _parse_timestamp(value) -> Optional[datetime]:
        """Parse a timestamp value into a datetime.

        Handles millisecond epoch ints, ISO 8601 strings, and date strings
        like '2025-12-01'.
        """
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value / 1000.0)
            if isinstance(value, str):
                # Try ISO format first (e.g. "2025-12-01T00:00:00Z")
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    pass
                # Try plain date format (e.g. "2025-12-01")
                return datetime.strptime(value, "%Y-%m-%d")
        except (ValueError, OSError):
            pass
        return None

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

        # End date includes tomorrow to cover timezone differences (server may be
        # in UTC while Garmin activities use the user's local time)
        end = end_date or (date.today() + timedelta(days=1))
        # Track the actual sync date separately (never store a future date)
        self._sync_date = min(end, date.today())

        # Determine start date based on mode
        if mode == "incremental":
            # Get last sync date for this category (per-user if user_id is set)
            last_sync = await self.db.get_last_sync_date(
                self.category, user_id=self.user_id
            )

            if last_sync:
                # Re-sync from last sync date (not +1) to catch activities
                # added on the same day after the previous sync ran
                start = last_sync
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
        # Use _sync_date (capped at today) to prevent storing future dates
        # that would break incremental sync start calculations
        actual_date = getattr(self, "_sync_date", last_date)
        await self.db.update_sync_state(
            category=self.category,
            last_sync_date=actual_date,
            records_synced=records_count,
            sync_status=sync_status,
            error_message=error_message,
            user_id=self.user_id,
        )
