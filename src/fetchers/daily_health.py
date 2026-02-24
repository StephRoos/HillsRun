"""Daily health data fetcher."""

import logging
import json
from datetime import date, timedelta, datetime
from typing import Optional, Tuple, Dict, Any, List

from .base import BaseFetcher

logger = logging.getLogger(__name__)


class DailyHealthFetcher(BaseFetcher):
    """Fetcher for daily health data (steps, heart rate, sleep, stress, body battery)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = "daily_health"

    async def fetch(
        self,
        mode: str = "incremental",
        days_back: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[int, Optional[str]]:
        """Fetch daily health data.

        Args:
            mode: Sync mode ('incremental' or 'full')
            days_back: Number of days to go back for full sync
            start_date: Optional override start date
            end_date: Optional override end date

        Returns:
            Tuple of (records_count, error_message)
        """
        start, end = await self.determine_date_range(mode, days_back, start_date, end_date)
        logger.info(f"Fetching daily health data from {start} to {end}")

        records_count = 0
        errors = []
        current_date = start

        while current_date <= end:
            date_str = current_date.isoformat()

            try:
                # Fetch daily summary
                await self._fetch_daily_summary(current_date, date_str)
                records_count += 1
            except Exception as e:
                logger.error(f"Error fetching daily summary for {date_str}: {e}")
                errors.append(str(e))

            for name, method in [
                ("heart_rate", self._fetch_heart_rate),
                ("sleep", self._fetch_sleep),
                ("stress", self._fetch_stress),
                ("body_battery", self._fetch_body_battery),
            ]:
                try:
                    await method(current_date, date_str)
                except Exception as e:
                    logger.warning(f"Error fetching {name} for {date_str}: {e}")

            current_date += timedelta(days=1)

        # Update sync state
        error_message = "; ".join(errors) if errors else None
        await self.update_sync_state(end, records_count, error_message)

        return records_count, error_message

    async def _fetch_daily_summary(self, current_date: date, date_str: str) -> None:
        """Fetch and store daily summary."""
        success, data, error = self.garmin_client.get_user_summary(date_str)

        if not success:
            logger.warning(f"Failed to get daily summary for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            logger.debug(f"No daily summary data for {date_str}")
            return

        # Transform and store data
        summary_data = self._transform_daily_summary(current_date, data)
        await self.db.upsert_daily_summary(self.user_id, summary_data)
        logger.debug(f"Stored daily summary for {date_str}")

    def _transform_daily_summary(self, calendar_date: date, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform daily summary data for database."""
        return {
            "calendar_date": calendar_date,
            "total_steps": data.get("totalSteps"),
            "step_goal": data.get("dailyStepGoal"),
            "total_distance_meters": data.get("totalDistanceMeters"),
            "active_calories": data.get("activeKilocalories"),
            "bmr_calories": data.get("bmrKilocalories"),
            "total_calories": data.get("totalKilocalories"),
            "floors_ascended": data.get("floorsAscended"),
            "floors_descended": data.get("floorsDescended"),
            "floors_goal": data.get("floorsAscendedGoal"),
            "moderate_intensity_minutes": data.get("moderateIntensityMinutes"),
            "vigorous_intensity_minutes": data.get("vigorousIntensityMinutes"),
            "intensity_minutes_goal": data.get("intensityMinutesGoal"),
            "highly_active_seconds": data.get("highlyActiveSeconds"),
            "active_seconds": data.get("activeSeconds"),
            "sedentary_seconds": data.get("sedentarySeconds"),
            "sleeping_seconds": data.get("sleepingSeconds"),
            "max_heart_rate": data.get("maxHeartRate"),
            "min_heart_rate": data.get("minHeartRate"),
            "resting_heart_rate": data.get("restingHeartRate"),
            "average_heart_rate": data.get("averageHeartRate"),
            "average_stress_level": data.get("averageStressLevel"),
            "max_stress_level": data.get("maxStressLevel"),
            "stress_qualifier": data.get("stressQualifier"),
        }

    async def _fetch_heart_rate(self, current_date: date, date_str: str) -> None:
        """Fetch and store heart rate samples."""
        success, data, error = self.garmin_client.get_heart_rates(date_str)

        if not success:
            logger.warning(f"Failed to get heart rates for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            logger.debug(f"No heart rate data for {date_str}")
            return

        # Extract heart rate samples
        samples = self._transform_heart_rate_samples(data)
        if samples:
            count = await self.db.upsert_heart_rate_samples(self.user_id, samples)
            logger.debug(f"Stored {count} heart rate samples for {date_str}")

    def _transform_heart_rate_samples(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform heart rate samples for database."""
        samples = []

        # Heart rate values can be in different formats
        hr_values = data.get("heartRateValues")
        if not hr_values:
            return samples

        for entry in hr_values:
            try:
                if isinstance(entry, dict):
                    timestamp_ms = entry.get("timestamp")
                    hr_value = entry.get("heartRate")
                elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    timestamp_ms = entry[0]
                    hr_value = entry[1]
                else:
                    continue

                if timestamp_ms and hr_value and hr_value > 0:
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)
                    samples.append({
                        "timestamp": timestamp,
                        "heart_rate": hr_value,
                    })
            except (TypeError, ValueError, IndexError):
                continue

        return samples

    async def _fetch_sleep(self, current_date: date, date_str: str) -> None:
        """Fetch and store sleep data."""
        success, data, error = self.garmin_client.get_sleep_data(date_str)

        if not success:
            logger.warning(f"Failed to get sleep data for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            logger.debug(f"No sleep data for {date_str}")
            return

        # Transform and store data
        sleep_data = self._transform_sleep_data(current_date, data)
        await self.db.upsert_sleep_data(self.user_id, sleep_data)
        logger.debug(f"Stored sleep data for {date_str}")

    def _transform_sleep_data(self, calendar_date: date, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform sleep data for database."""
        daily_sleep_dto = data.get("dailySleepDTO", {})
        sleep_movement = data.get("sleepMovement", [])

        sleep_start = self._parse_timestamp(daily_sleep_dto.get("sleepStartTimestampGMT"))
        sleep_end = self._parse_timestamp(daily_sleep_dto.get("sleepEndTimestampGMT"))

        return {
            "calendar_date": calendar_date,
            "sleep_start_timestamp": sleep_start,
            "sleep_end_timestamp": sleep_end,
            "total_sleep_seconds": daily_sleep_dto.get("sleepTimeSeconds"),
            "deep_sleep_seconds": daily_sleep_dto.get("deepSleepSeconds"),
            "light_sleep_seconds": daily_sleep_dto.get("lightSleepSeconds"),
            "rem_sleep_seconds": daily_sleep_dto.get("remSleepSeconds"),
            "awake_seconds": daily_sleep_dto.get("awakeSleepSeconds"),
            "sleep_score": daily_sleep_dto.get("sleepScores", {}).get("overall", {}).get("value"),
            "sleep_quality": daily_sleep_dto.get("sleepScores", {}).get("overall", {}).get("qualifierKey"),
            "sleep_levels": json.dumps(sleep_movement) if sleep_movement else None,
        }

    async def _fetch_stress(self, current_date: date, date_str: str) -> None:
        """Fetch and store stress data."""
        success, data, error = self.garmin_client.get_stress_data(date_str)

        if not success:
            logger.warning(f"Failed to get stress data for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            logger.debug(f"No stress data for {date_str}")
            return

        # Transform and store data
        stress_data = self._transform_stress_data(current_date, data)
        await self.db.upsert_stress_data(self.user_id, stress_data)
        logger.debug(f"Stored stress data for {date_str}")

    def _transform_stress_data(self, calendar_date: date, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform stress data for database."""
        return {
            "calendar_date": calendar_date,
            "average_stress_level": data.get("averageStressLevel"),
            "max_stress_level": data.get("maxStressLevel"),
            "rest_stress_duration_seconds": data.get("restStressDuration"),
            "activity_stress_duration_seconds": data.get("activityStressDuration"),
            "uncategorized_stress_duration_seconds": data.get("uncategorizedStressDuration"),
            "low_stress_duration_seconds": data.get("lowStressDuration"),
            "medium_stress_duration_seconds": data.get("mediumStressDuration"),
            "high_stress_duration_seconds": data.get("highStressDuration"),
            "stress_chart_values": json.dumps(data.get("stressValuesArray")) if data.get("stressValuesArray") else None,
        }

    async def _fetch_body_battery(self, current_date: date, date_str: str) -> None:
        """Fetch and store body battery data."""
        success, data, error = self.garmin_client.get_body_battery(date_str)

        if not success:
            logger.warning(f"Failed to get body battery for {date_str}: {error}")
            return

        data = self._ensure_dict(data)
        if not data:
            logger.debug(f"No body battery data for {date_str}")
            return

        # Transform and store data
        bb_data = self._transform_body_battery_data(current_date, data)
        await self.db.upsert_body_battery(self.user_id, bb_data)
        logger.debug(f"Stored body battery data for {date_str}")

    def _transform_body_battery_data(self, calendar_date: date, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform body battery data for database."""
        start_ts = self._parse_timestamp(data.get("startTimestampGMT"))
        end_ts = self._parse_timestamp(data.get("endTimestampGMT"))

        return {
            "calendar_date": calendar_date,
            "charged_value": data.get("charged"),
            "drained_value": data.get("drained"),
            "highest_value": data.get("highestValue"),
            "lowest_value": data.get("lowestValue"),
            "start_timestamp": start_ts,
            "end_timestamp": end_ts,
            "body_battery_values": json.dumps(data.get("bodyBatteryValuesArray")) if data.get("bodyBatteryValuesArray") else None,
        }
