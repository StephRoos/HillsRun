"""Wellness data fetcher."""

import logging
import json
from datetime import date, timedelta
from typing import Optional, Tuple, Dict, Any

from .base import BaseFetcher

logger = logging.getLogger(__name__)


class WellnessFetcher(BaseFetcher):
    """Fetcher for wellness data (hydration, body battery additional data)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = "wellness"

    async def fetch(
        self,
        mode: str = "incremental",
        days_back: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[int, Optional[str]]:
        """Fetch wellness data.

        Args:
            mode: Sync mode ('incremental' or 'full')
            days_back: Number of days to go back for full sync
            start_date: Optional override start date
            end_date: Optional override end date

        Returns:
            Tuple of (records_count, error_message)
        """
        start, end = await self.determine_date_range(mode, days_back, start_date, end_date)
        logger.info(f"Fetching wellness data from {start} to {end}")

        records_count = 0
        errors = []
        current_date = start

        while current_date <= end:
            date_str = current_date.isoformat()

            try:
                # Fetch hydration data
                await self._fetch_hydration(current_date, date_str)
                records_count += 1

            except Exception as e:
                error_msg = f"Error fetching wellness data for {date_str}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

            current_date += timedelta(days=1)

        # Update sync state
        error_message = "; ".join(errors) if errors else None
        await self.update_sync_state(end, records_count, error_message)

        return records_count, error_message

    async def _fetch_hydration(self, current_date: date, date_str: str) -> None:
        """Fetch and store hydration data."""
        success, data, error = self.garmin_client.get_hydration_data(date_str)

        if not success:
            logger.debug(f"No hydration data for {date_str}: {error}")
            return

        if not data:
            return

        # Transform and store
        hydration_data = self._transform_hydration_data(current_date, data)
        await self.db.upsert_hydration_data(self.user_id, hydration_data)
        logger.debug(f"Stored hydration data for {date_str}")

    def _transform_hydration_data(self, calendar_date: date, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform hydration data for database."""
        return {
            "calendar_date": calendar_date,
            "total_hydration_ml": data.get("valueInML"),
            "hydration_goal_ml": data.get("goalInML"),
            "hydration_entries": json.dumps(data.get("hydrationLog")) if data.get("hydrationLog") else None,
        }
