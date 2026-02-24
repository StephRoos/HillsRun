"""Advanced metrics data fetcher."""

import logging
import json
from datetime import date, timedelta, datetime
from typing import Optional, Tuple, Dict, Any

from .base import BaseFetcher

logger = logging.getLogger(__name__)


class AdvancedMetricsFetcher(BaseFetcher):
    """Fetcher for advanced metrics (HRV, SpO2, VO2 Max, respiration, training readiness)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = "advanced_metrics"

    async def fetch(
        self,
        mode: str = "incremental",
        days_back: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[int, Optional[str]]:
        """Fetch advanced metrics data.

        Args:
            mode: Sync mode ('incremental' or 'full')
            days_back: Number of days to go back for full sync
            start_date: Optional override start date
            end_date: Optional override end date

        Returns:
            Tuple of (records_count, error_message)
        """
        start, end = await self.determine_date_range(
            mode, days_back, start_date, end_date
        )
        logger.info(f"Fetching advanced metrics from {start} to {end}")

        records_count = 0
        errors = []
        current_date = start

        while current_date <= end:
            date_str = current_date.isoformat()

            try:
                # Fetch HRV data
                await self._fetch_hrv(current_date, date_str)

                # Fetch SpO2 data
                await self._fetch_spo2(current_date, date_str)

                # Fetch VO2 Max and fitness metrics
                await self._fetch_fitness_metrics(current_date, date_str)

                # Fetch respiration data
                await self._fetch_respiration(current_date, date_str)

                # Fetch training readiness
                await self._fetch_training_readiness(current_date, date_str)

                records_count += 1

            except Exception as e:
                error_msg = f"Error fetching advanced metrics for {date_str}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

            current_date += timedelta(days=1)

        # Update sync state
        error_message = "; ".join(errors) if errors else None
        await self.update_sync_state(end, records_count, error_message)

        return records_count, error_message

    async def _fetch_hrv(self, current_date: date, date_str: str) -> None:
        """Fetch and store HRV data."""
        success, data, error = self.garmin_client.get_hrv_data(date_str)

        if not success:
            logger.debug(f"No HRV data for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            return

        # HRV response wraps summary under "hrvSummary"
        summary = data.get("hrvSummary")
        if not summary:
            logger.debug(f"No hrvSummary in HRV data for {date_str}")
            return

        # Transform and store
        hrv_data = self._transform_hrv_data(current_date, summary)
        await self.db.upsert_hrv_data(self.user_id, hrv_data)
        logger.debug(f"Stored HRV data for {date_str}")

    def _transform_hrv_data(
        self, calendar_date: date, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform HRV data for database.

        Args:
            calendar_date: The date for this record.
            data: Raw data from Garmin API.

        Returns:
            Dict with DB column names as keys.
        """
        return {
            "calendar_date": calendar_date,
            "weekly_avg": data.get("weeklyAvg"),
            "last_night_avg": data.get("lastNightAvg"),
            "last_night_5_min_high": data.get("lastNight5MinHigh"),
            "hrv_status": data.get("status"),
            "feedback_phrase": data.get("feedbackPhrase"),
        }

    async def _fetch_spo2(self, current_date: date, date_str: str) -> None:
        """Fetch and store SpO2 data."""
        success, data, error = self.garmin_client.get_spo2_data(date_str)

        if not success:
            logger.debug(f"No SpO2 data for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            return

        # Transform and store
        spo2_data = self._transform_spo2_data(current_date, data)
        await self.db.upsert_spo2_data(self.user_id, spo2_data)
        logger.debug(f"Stored SpO2 data for {date_str}")

    def _transform_spo2_data(
        self, calendar_date: date, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform SpO2 data for database.

        Args:
            calendar_date: The date for this record.
            data: Raw data from Garmin API.

        Returns:
            Dict with DB column names as keys.
        """
        # Parse latest reading timestamp
        latest_ts = None
        if data.get("latestSpO2ReadingTimeGMT"):
            latest_ts = datetime.fromtimestamp(
                data["latestSpO2ReadingTimeGMT"] / 1000.0
            )

        return {
            "calendar_date": calendar_date,
            "average_spo2_percentage": data.get("averageSPO2"),
            "lowest_spo2_percentage": data.get("lowestSPO2"),
            "latest_spo2_reading": data.get("latestSpO2"),
            "latest_spo2_reading_timestamp": latest_ts,
            "spo2_values": json.dumps(data.get("spO2ValuesArray"))
            if data.get("spO2ValuesArray")
            else None,
        }

    async def _fetch_fitness_metrics(self, current_date: date, date_str: str) -> None:
        """Fetch and store fitness metrics (VO2 Max, etc.)."""
        success, data, error = self.garmin_client.get_max_metrics(date_str)

        if not success:
            logger.debug(f"No fitness metrics for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            return

        # Transform and store
        fitness_data = self._transform_fitness_metrics(current_date, data)
        await self.db.upsert_fitness_metrics(self.user_id, fitness_data)
        logger.debug(f"Stored fitness metrics for {date_str}")

    def _transform_fitness_metrics(
        self, calendar_date: date, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform fitness metrics for database.

        Args:
            calendar_date: The date for this record.
            data: Raw data from Garmin API.

        Returns:
            Dict with DB column names as keys.
        """
        return {
            "calendar_date": calendar_date,
            "vo2_max": data.get("vo2Max"),
            "vo2_max_running": data.get("vo2MaxRunning"),
            "vo2_max_cycling": data.get("vo2MaxCycling"),
            "fitness_age": data.get("fitnessAge"),
            "lactate_threshold_bpm": data.get("lactateThresholdHeartRate"),
            "lactate_threshold_speed": data.get("lactateThresholdSpeed"),
        }

    async def _fetch_respiration(self, current_date: date, date_str: str) -> None:
        """Fetch and store respiration data."""
        success, data, error = self.garmin_client.get_respiration_data(date_str)

        if not success:
            logger.debug(f"No respiration data for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            return

        # Transform and store
        resp_data = self._transform_respiration_data(current_date, data)
        await self.db.upsert_respiration_data(self.user_id, resp_data)
        logger.debug(f"Stored respiration data for {date_str}")

    def _transform_respiration_data(
        self, calendar_date: date, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform respiration data for database.

        Args:
            calendar_date: The date for this record.
            data: Raw data from Garmin API.

        Returns:
            Dict with DB column names as keys.
        """
        return {
            "calendar_date": calendar_date,
            "avg_waking_respiration_rate": data.get("avgWakingRespirationRate"),
            "max_waking_respiration_rate": data.get("maxWakingRespirationRate"),
            "min_waking_respiration_rate": data.get("minWakingRespirationRate"),
            "avg_sleep_respiration_rate": data.get("avgSleepRespirationRate"),
        }

    async def _fetch_training_readiness(
        self, current_date: date, date_str: str
    ) -> None:
        """Fetch and store training readiness data."""
        success, data, error = self.garmin_client.get_training_readiness(date_str)

        if not success:
            logger.debug(f"No training readiness for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            return

        tr_data = {
            "calendar_date": current_date,
            "score": data.get("score") or data.get("readinessScore"),
            "score_feedback": data.get("scoreFeedback")
            or data.get("readinessFeedback"),
            "hrv_status": data.get("hrvStatus"),
            "sleep_score": data.get("sleepScore") or data.get("sleepScoreValue"),
            "recent_training_load": data.get("recentTrainingLoad")
            or data.get("acuteTrainingLoad"),
            "acute_load": data.get("acuteLoad") or data.get("acuteTrainingLoadScore"),
            "chronic_load": data.get("chronicLoad") or data.get("chronicTrainingLoad"),
        }
        await self.db.upsert_training_readiness(self.user_id, tr_data)
        logger.debug(f"Stored training readiness for {date_str}")
