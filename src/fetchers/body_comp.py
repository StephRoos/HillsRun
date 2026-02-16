"""Body composition data fetcher."""

import logging
from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any

from .base import BaseFetcher

logger = logging.getLogger(__name__)


class BodyCompositionFetcher(BaseFetcher):
    """Fetcher for body composition and weight data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = "body_composition"

    async def fetch(
        self,
        mode: str = "incremental",
        days_back: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[int, Optional[str]]:
        """Fetch body composition data.

        Args:
            mode: Sync mode ('incremental' or 'full')
            days_back: Number of days to go back for full sync
            start_date: Optional override start date
            end_date: Optional override end date

        Returns:
            Tuple of (records_count, error_message)
        """
        start, end = await self.determine_date_range(mode, days_back, start_date, end_date)
        logger.info(f"Fetching body composition from {start} to {end}")

        records_count = 0
        errors = []

        try:
            # Fetch weigh-ins
            success, weigh_ins, error = self.garmin_client.get_weigh_ins(start, end)

            if not success:
                error_msg = f"Failed to get weigh-ins: {error}"
                logger.warning(error_msg)
                errors.append(error_msg)
            elif weigh_ins:
                for weigh_in in weigh_ins:
                    try:
                        body_comp_data = self._transform_body_composition(weigh_in)
                        await self.db.upsert_body_composition(self.user_id, body_comp_data)
                        records_count += 1
                    except Exception as e:
                        error_msg = f"Error processing weigh-in: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)

                logger.info(f"Stored {records_count} body composition records")

        except Exception as e:
            error_msg = f"Error fetching body composition: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Update sync state
        error_message = "; ".join(errors) if errors else None
        await self.update_sync_state(end, records_count, error_message)

        return records_count, error_message

    def _transform_body_composition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform body composition data for database."""
        # Parse timestamp
        timestamp = None
        if data.get("date"):
            timestamp = datetime.fromtimestamp(data["date"] / 1000.0)
        elif data.get("timestampGMT"):
            timestamp = datetime.fromtimestamp(data["timestampGMT"] / 1000.0)

        return {
            "timestamp": timestamp,
            "weight_kg": data.get("weight"),
            "bmi": data.get("bmi"),
            "body_fat_percentage": data.get("bodyFat"),
            "body_water_percentage": data.get("bodyWater"),
            "bone_mass_kg": data.get("boneMass"),
            "muscle_mass_kg": data.get("muscleMass"),
            "metabolic_age": data.get("metabolicAge"),
            "visceral_fat_rating": data.get("visceralFatMass") or data.get("visceralFatRating"),
            "basal_met": data.get("bmr"),
            "active_met": data.get("activeMet") or data.get("activeMetabolicRate"),
            "physique_rating": data.get("physiqueRating"),
            "source_type": data.get("sourceType"),
        }
