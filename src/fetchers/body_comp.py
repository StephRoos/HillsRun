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
        """Fetch body composition data."""
        start, end = await self.determine_date_range(mode, days_back, start_date, end_date)
        logger.info(f"Fetching body composition from {start} to {end}")

        records_count = 0
        errors = []

        try:
            success, response, error = self.garmin_client.get_weigh_ins(start, end)

            if not success:
                logger.warning(f"Failed to get weigh-ins: {error}")
                errors.append(f"Failed to get weigh-ins: {error}")
            elif response:
                # Response structure:
                # { "dailyWeightSummaries": [
                #     { "summaryDate": "2025-12-01", "latestWeight": {...},
                #       "allWeightMetrics": [...] }
                #   ], ... }
                summaries = []
                if isinstance(response, dict):
                    summaries = response.get("dailyWeightSummaries") or []
                elif isinstance(response, list):
                    summaries = response

                for summary in summaries:
                    if not isinstance(summary, dict):
                        continue
                    try:
                        body_comp_data = self._transform_daily_weight(summary)
                        if body_comp_data.get("timestamp"):
                            await self.db.upsert_body_composition(self.user_id, body_comp_data)
                            records_count += 1
                    except Exception as e:
                        logger.error(f"Error processing weigh-in for {summary.get('summaryDate')}: {e}")
                        errors.append(str(e))

                logger.info(f"Stored {records_count} body composition records")

        except Exception as e:
            logger.error(f"Error fetching body composition: {e}")
            errors.append(str(e))

        error_message = "; ".join(errors) if errors else None
        await self.update_sync_state(end, records_count, error_message)
        return records_count, error_message

    @staticmethod
    def _parse_date(value) -> Optional[datetime]:
        """Parse a date string like '2025-12-01' into datetime."""
        if not value:
            return None
        try:
            if isinstance(value, str):
                return datetime.strptime(value, "%Y-%m-%d")
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value / 1000.0)
        except (ValueError, OSError):
            pass
        return None

    def _transform_daily_weight(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform daily weight summary for database.

        Structure: { summaryDate, numOfWeightEntries, minWeight, maxWeight,
                     latestWeight: { weight, bmi, bodyFat, ... },
                     allWeightMetrics: [...] }
        """
        timestamp = self._parse_date(data.get("summaryDate"))

        # Get detailed metrics from latestWeight (may be a dict or absent)
        latest = data.get("latestWeight")
        if not isinstance(latest, dict):
            latest = {}

        def grams_to_kg(val, threshold=500):
            """Convert grams to kg if value exceeds threshold."""
            if val and isinstance(val, (int, float)) and val > threshold:
                return round(val / 1000.0, 2)
            return val

        # Weight: try latestWeight dict, then minWeight/maxWeight from summary
        weight = grams_to_kg(latest.get("weight") or data.get("minWeight") or data.get("maxWeight"))

        return {
            "timestamp": timestamp,
            "weight_kg": weight,
            "bmi": latest.get("bmi"),
            "body_fat_percentage": latest.get("bodyFat"),
            "body_water_percentage": latest.get("bodyWater"),
            "bone_mass_kg": grams_to_kg(latest.get("boneMass"), threshold=100),
            "muscle_mass_kg": grams_to_kg(latest.get("muscleMass"), threshold=200),
            "metabolic_age": latest.get("metabolicAge"),
            "visceral_fat_rating": latest.get("visceralFatMass") or latest.get("visceralFatRating"),
            "basal_met": latest.get("bmr"),
            "active_met": latest.get("activeMet"),
            "physique_rating": latest.get("physiqueRating"),
            "source_type": latest.get("sourceType"),
        }
