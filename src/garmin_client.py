"""Garmin Connect API client wrapper."""

import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from garminconnect import Garmin, GarminConnectAuthenticationError
import garth

from .config import GarminConfig
from .utils.retry import retry_api_call, safe_api_call

logger = logging.getLogger(__name__)


class GarminClient:
    """Wrapper for Garmin Connect API with retry logic and rate limiting."""

    def __init__(self, config: GarminConfig, rate_limit_delay: float = 0.5):
        """Initialize Garmin client.

        Args:
            config: Garmin configuration
            rate_limit_delay: Delay between API calls in seconds
        """
        self.config = config
        self.rate_limit_delay = rate_limit_delay
        self.client: Optional[Garmin] = None
        self._last_request_time = 0.0

    def connect(self) -> None:
        """Connect to Garmin Connect using stored tokens."""
        try:
            # Configure garth to use custom tokens directory
            garth.resume(self.config.tokens_dir)
            logger.info(f"Loaded Garmin tokens from {self.config.tokens_dir}")

            # Initialize Garmin client without credentials (using tokens)
            self.client = Garmin()

            # Test connection
            self.client.get_user_profile()
            logger.info("Successfully connected to Garmin Connect")

        except FileNotFoundError:
            logger.error(
                f"Garmin tokens not found in {self.config.tokens_dir}. "
                "Please authenticate first using the garminconnect CLI."
            )
            raise GarminConnectAuthenticationError("Garmin tokens not found")

        except Exception as e:
            logger.error(f"Failed to connect to Garmin Connect: {e}")
            raise

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    # ============================================
    # User Profile
    # ============================================

    @safe_api_call
    @retry_api_call
    def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile information."""
        self._rate_limit()
        return self.client.get_full_name()

    # ============================================
    # Daily Health Data
    # ============================================

    @safe_api_call
    @retry_api_call
    def get_user_summary(self, date_str: str) -> Dict[str, Any]:
        """Get user summary for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            User summary data
        """
        self._rate_limit()
        return self.client.get_user_summary(date_str)

    @safe_api_call
    @retry_api_call
    def get_heart_rates(self, date_str: str) -> Dict[str, Any]:
        """Get heart rate data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Heart rate data
        """
        self._rate_limit()
        return self.client.get_heart_rates(date_str)

    @safe_api_call
    @retry_api_call
    def get_sleep_data(self, date_str: str) -> Dict[str, Any]:
        """Get sleep data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Sleep data
        """
        self._rate_limit()
        return self.client.get_sleep_data(date_str)

    @safe_api_call
    @retry_api_call
    def get_stress_data(self, date_str: str) -> Dict[str, Any]:
        """Get stress data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Stress data
        """
        self._rate_limit()
        return self.client.get_stress_data(date_str)

    @safe_api_call
    @retry_api_call
    def get_body_battery(self, date_str: str) -> Dict[str, Any]:
        """Get body battery data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Body battery data
        """
        self._rate_limit()
        return self.client.get_body_battery(date_str)

    # ============================================
    # Body Composition
    # ============================================

    @safe_api_call
    @retry_api_call
    def get_weigh_ins(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get weigh-in data for date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of weigh-in records
        """
        self._rate_limit()
        return self.client.get_weigh_ins(start_date, end_date)

    @safe_api_call
    @retry_api_call
    def get_body_composition(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get body composition data for date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Body composition data
        """
        self._rate_limit()
        return self.client.get_body_composition(start_date, end_date)

    # ============================================
    # Advanced Metrics
    # ============================================

    @safe_api_call
    @retry_api_call
    def get_hrv_data(self, date_str: str) -> Dict[str, Any]:
        """Get HRV data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            HRV data
        """
        self._rate_limit()
        return self.client.get_hrv_data(date_str)

    @safe_api_call
    @retry_api_call
    def get_spo2_data(self, date_str: str) -> Dict[str, Any]:
        """Get SpO2 data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            SpO2 data
        """
        self._rate_limit()
        return self.client.get_spo2_data(date_str)

    @safe_api_call
    @retry_api_call
    def get_max_metrics(self, date_str: str) -> Dict[str, Any]:
        """Get max metrics (VO2 Max, etc.) for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Max metrics data
        """
        self._rate_limit()
        return self.client.get_max_metrics(date_str)

    @safe_api_call
    @retry_api_call
    def get_respiration_data(self, date_str: str) -> Dict[str, Any]:
        """Get respiration data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Respiration data
        """
        self._rate_limit()
        return self.client.get_respiration_data(date_str)

    @safe_api_call
    @retry_api_call
    def get_training_readiness(self, date_str: str) -> Dict[str, Any]:
        """Get training readiness for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Training readiness data
        """
        self._rate_limit()
        return self.client.get_training_readiness(date_str)

    # ============================================
    # Activities
    # ============================================

    @safe_api_call
    @retry_api_call
    def get_activities_by_date(
        self, start_date: date, end_date: date, activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get activities for date range.

        Args:
            start_date: Start date
            end_date: End date
            activity_type: Optional activity type filter

        Returns:
            List of activities
        """
        self._rate_limit()
        return self.client.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat(), activity_type
        )

    @safe_api_call
    @retry_api_call
    def get_activity(self, activity_id: int) -> Dict[str, Any]:
        """Get detailed activity data.

        Args:
            activity_id: Activity ID

        Returns:
            Activity details
        """
        self._rate_limit()
        return self.client.get_activity(activity_id)

    @safe_api_call
    @retry_api_call
    def get_activity_splits(self, activity_id: int) -> Dict[str, Any]:
        """Get activity splits/laps.

        Args:
            activity_id: Activity ID

        Returns:
            Activity splits
        """
        self._rate_limit()
        return self.client.get_activity_splits(activity_id)

    # ============================================
    # Wellness
    # ============================================

    @safe_api_call
    @retry_api_call
    def get_hydration_data(self, date_str: str) -> Dict[str, Any]:
        """Get hydration data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Hydration data
        """
        self._rate_limit()
        return self.client.get_hydration_data(date_str)

    @safe_api_call
    @retry_api_call
    def get_blood_pressure(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get blood pressure data for date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of blood pressure readings
        """
        self._rate_limit()
        return self.client.get_blood_pressure(start_date, end_date)
