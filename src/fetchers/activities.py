"""Activities data fetcher."""

import logging
import json
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Dict, Any, Set

from .base import BaseFetcher

logger = logging.getLogger(__name__)


class ActivitiesFetcher(BaseFetcher):
    """Fetcher for activities data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = "activities"

    async def fetch(
        self,
        mode: str = "incremental",
        days_back: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[int, Optional[str]]:
        """Fetch activities data.

        Args:
            mode: Sync mode ('incremental' or 'full')
            days_back: Number of days to go back for full sync
            start_date: Optional override start date
            end_date: Optional override end date

        Returns:
            Tuple of (records_count, error_message)
        """
        start, end = await self.determine_date_range(mode, days_back, start_date, end_date)
        logger.info(f"Fetching activities from {start} to {end}")

        records_count = 0
        errors = []
        garmin_activity_ids: Set[int] = set()

        try:
            # Fetch activities for date range
            success, activities, error = self.garmin_client.get_activities_by_date(start, end)

            if not success:
                error_msg = f"Failed to get activities: {error}"
                logger.error(error_msg)
                errors.append(error_msg)
                return 0, error_msg

            if activities:
                # Process each activity
                for activity in activities:
                    try:
                        activity_id = activity.get("activityId")
                        if activity_id:
                            garmin_activity_ids.add(activity_id)
                        await self._process_activity(activity)
                        records_count += 1
                    except Exception as e:
                        error_msg = f"Error processing activity {activity.get('activityId')}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)

            # Remove activities deleted from Garmin.
            # In incremental mode, the fetch range is narrow (last_sync+1 to today),
            # so deletions outside that range would be missed. Use a broader range
            # for the deletion check (last days_back days) with one extra API call.
            if mode == "incremental" and start > end - timedelta(days=days_back):
                deletion_start = end - timedelta(days=days_back)
                logger.info(f"Checking deletions over broader range: {deletion_start} to {end}")
                success_del, all_activities, err_del = self.garmin_client.get_activities_by_date(deletion_start, end)
                if success_del and all_activities is not None:
                    all_garmin_ids = {a.get("activityId") for a in all_activities if a.get("activityId")}
                    db_ids = await self.db.get_activity_ids_for_range(self.user_id, deletion_start, end)
                    to_delete = [aid for aid in db_ids if aid not in all_garmin_ids]
                else:
                    to_delete = []
            else:
                db_activity_ids = await self.db.get_activity_ids_for_range(self.user_id, start, end)
                to_delete = [aid for aid in db_activity_ids if aid not in garmin_activity_ids]

            if to_delete:
                deleted = await self.db.delete_activities(to_delete, self.user_id)
                logger.info(f"Deleted {deleted} activities removed from Garmin")

        except Exception as e:
            error_msg = f"Error fetching activities: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Update sync state
        error_message = "; ".join(errors) if errors else None
        await self.update_sync_state(end, records_count, error_message)

        return records_count, error_message

    async def _process_activity(self, activity: Dict[str, Any]) -> None:
        """Process and store a single activity."""
        activity_id = activity.get("activityId")

        # Get detailed activity data
        success, details, error = self.garmin_client.get_activity(activity_id)
        if success and details:
            activity.update(details)

        # Transform and store activity
        activity_data = self._transform_activity(activity)
        await self.db.upsert_activity(self.user_id, activity_data)
        logger.debug(f"Stored activity {activity_id}")

    def _transform_activity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform activity data for database."""
        # Parse start timestamp
        start_ts = None
        if data.get("startTimeGMT"):
            start_ts = datetime.fromisoformat(data["startTimeGMT"].replace("Z", "+00:00"))
        elif data.get("beginTimestamp"):
            start_ts = datetime.fromtimestamp(data["beginTimestamp"] / 1000.0)

        return {
            "activity_id": data.get("activityId"),
            "activity_name": data.get("activityName"),
            "activity_type": data.get("activityType", {}).get("typeKey") if isinstance(data.get("activityType"), dict) else data.get("activityType"),
            "sport_type": (
                (data.get("sportTypeKey") if data.get("sportTypeKey") not in (None, "uncategorized") else None)
                or (data.get("activityType", {}).get("typeKey") if isinstance(data.get("activityType"), dict) else data.get("activityType"))
                or data.get("eventType", {}).get("typeKey")
            ),
            "start_timestamp": start_ts,
            "duration_seconds": data.get("duration") or data.get("elapsedDuration"),
            "distance_meters": data.get("distance"),
            "average_speed": data.get("averageSpeed"),
            "max_speed": data.get("maxSpeed"),
            "average_pace": data.get("averagePace"),
            "max_pace": data.get("maxPace"),
            "calories": data.get("calories"),
            "average_hr": data.get("averageHR"),
            "max_hr": data.get("maxHR"),
            "average_running_cadence": data.get("averageRunningCadenceInStepsPerMinute"),
            "max_running_cadence": data.get("maxRunningCadenceInStepsPerMinute"),
            "average_bike_cadence": data.get("averageBikingCadenceInRevPerMinute"),
            "max_bike_cadence": data.get("maxBikingCadenceInRevPerMinute"),
            "average_power": data.get("avgPower"),
            "max_power": data.get("maxPower"),
            "normalized_power": data.get("normalizedPower"),
            "training_stress_score": data.get("trainingStressScore"),
            "intensity_factor": data.get("intensityFactor"),
            "elevation_gain_meters": data.get("elevationGain"),
            "elevation_loss_meters": data.get("elevationLoss"),
            "min_elevation_meters": data.get("minElevation"),
            "max_elevation_meters": data.get("maxElevation"),
            "average_temperature": data.get("avgTemperature"),
            "max_temperature": data.get("maxTemperature"),
            "min_temperature": data.get("minTemperature"),
            "training_effect": data.get("trainingEffect"),
            "aerobic_training_effect": data.get("aerobicTrainingEffect"),
            "anaerobic_training_effect": data.get("anaerobicTrainingEffect"),
            "avg_vertical_oscillation": data.get("avgVerticalOscillation"),
            "avg_ground_contact_time": data.get("avgGroundContactTime"),
            "avg_stride_length": data.get("avgStrideLength"),
            "vo2_max_value": data.get("vO2MaxValue"),
            "lactate_threshold_bpm": data.get("lactateThresholdBpm"),
            "device_name": data.get("deviceName") or data.get("metadataDTO", {}).get("deviceName"),
            "description": data.get("description"),
            "manual_activity": data.get("manual", False),
            "pr": data.get("pr", False),
            "favorite": data.get("favorite", False),
            "auto_calc_calories": data.get("autoCalcCalories"),
            "num_laps": data.get("lapCount"),
            "activity_data": json.dumps(data),
        }
