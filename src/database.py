"""Database operations with asyncpg."""

import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import asyncpg

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


class Database:
    """Database connection and operations manager."""

    def __init__(self, config: DatabaseConfig):
        """Initialize database manager.

        Args:
            config: Database configuration
        """
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.pool_min_size,
                max_size=self.config.pool_max_size,
                command_timeout=60,
            )
            logger.info(f"Connected to database: {self.config.host}:{self.config.port}/{self.config.database}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    # ============================================
    # User Operations
    # ============================================

    async def get_or_create_user(
        self,
        garmin_user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> int:
        """Get or create user and return user_id.

        Args:
            garmin_user_id: Garmin user ID
            display_name: User display name
            email: User email

        Returns:
            User ID (internal)
        """
        query = """
            INSERT INTO garmin_user (garmin_user_id, display_name, email)
            VALUES ($1, $2, $3)
            ON CONFLICT (garmin_user_id) DO UPDATE
            SET display_name = COALESCE(EXCLUDED.display_name, garmin_user.display_name),
                email = COALESCE(EXCLUDED.email, garmin_user.email),
                updated_at = CURRENT_TIMESTAMP
            RETURNING user_id
        """
        user_id = await self.pool.fetchval(query, garmin_user_id, display_name, email)
        return user_id

    # ============================================
    # Sync State Operations
    # ============================================

    async def get_last_sync_date(self, category: str) -> Optional[date]:
        """Get last sync date for a category.

        Args:
            category: Sync category

        Returns:
            Last sync date or None if never synced
        """
        query = "SELECT last_sync_date FROM sync_state WHERE category = $1"
        result = await self.pool.fetchval(query, category)
        return result

    async def update_sync_state(
        self,
        category: str,
        last_sync_date: date,
        records_synced: int,
        sync_status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        """Update sync state for a category.

        Args:
            category: Sync category
            last_sync_date: Last successfully synced date
            records_synced: Number of records synced
            sync_status: Status (success, partial, failed)
            error_message: Optional error message
        """
        query = """
            INSERT INTO sync_state (category, last_sync_date, last_sync_timestamp, records_synced, sync_status, error_message)
            VALUES ($1, $2, CURRENT_TIMESTAMP, $3, $4, $5)
            ON CONFLICT (category) DO UPDATE
            SET last_sync_date = EXCLUDED.last_sync_date,
                last_sync_timestamp = CURRENT_TIMESTAMP,
                records_synced = EXCLUDED.records_synced,
                sync_status = EXCLUDED.sync_status,
                error_message = EXCLUDED.error_message
        """
        await self.pool.execute(
            query,
            category,
            last_sync_date,
            records_synced,
            sync_status,
            error_message,
        )
        logger.info(f"Updated sync state for {category}: {last_sync_date}, {records_synced} records")

    # ============================================
    # Daily Health Data Operations
    # ============================================

    async def upsert_daily_summary(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert daily summary data.

        Args:
            user_id: User ID
            data: Daily summary data
        """
        query = """
            INSERT INTO daily_summary (
                user_id, calendar_date, total_steps, step_goal, total_distance_meters,
                active_calories, bmr_calories, total_calories, floors_ascended, floors_descended,
                floors_goal, moderate_intensity_minutes, vigorous_intensity_minutes, intensity_minutes_goal,
                highly_active_seconds, active_seconds, sedentary_seconds, sleeping_seconds,
                max_heart_rate, min_heart_rate, resting_heart_rate, average_heart_rate,
                average_stress_level, max_stress_level, stress_qualifier
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, $23, $24, $25
            )
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                total_steps = EXCLUDED.total_steps,
                step_goal = EXCLUDED.step_goal,
                total_distance_meters = EXCLUDED.total_distance_meters,
                active_calories = EXCLUDED.active_calories,
                bmr_calories = EXCLUDED.bmr_calories,
                total_calories = EXCLUDED.total_calories,
                floors_ascended = EXCLUDED.floors_ascended,
                floors_descended = EXCLUDED.floors_descended,
                floors_goal = EXCLUDED.floors_goal,
                moderate_intensity_minutes = EXCLUDED.moderate_intensity_minutes,
                vigorous_intensity_minutes = EXCLUDED.vigorous_intensity_minutes,
                intensity_minutes_goal = EXCLUDED.intensity_minutes_goal,
                highly_active_seconds = EXCLUDED.highly_active_seconds,
                active_seconds = EXCLUDED.active_seconds,
                sedentary_seconds = EXCLUDED.sedentary_seconds,
                sleeping_seconds = EXCLUDED.sleeping_seconds,
                max_heart_rate = EXCLUDED.max_heart_rate,
                min_heart_rate = EXCLUDED.min_heart_rate,
                resting_heart_rate = EXCLUDED.resting_heart_rate,
                average_heart_rate = EXCLUDED.average_heart_rate,
                average_stress_level = EXCLUDED.average_stress_level,
                max_stress_level = EXCLUDED.max_stress_level,
                stress_qualifier = EXCLUDED.stress_qualifier,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("total_steps"),
            data.get("step_goal"),
            data.get("total_distance_meters"),
            data.get("active_calories"),
            data.get("bmr_calories"),
            data.get("total_calories"),
            data.get("floors_ascended"),
            data.get("floors_descended"),
            data.get("floors_goal"),
            data.get("moderate_intensity_minutes"),
            data.get("vigorous_intensity_minutes"),
            data.get("intensity_minutes_goal"),
            data.get("highly_active_seconds"),
            data.get("active_seconds"),
            data.get("sedentary_seconds"),
            data.get("sleeping_seconds"),
            data.get("max_heart_rate"),
            data.get("min_heart_rate"),
            data.get("resting_heart_rate"),
            data.get("average_heart_rate"),
            data.get("average_stress_level"),
            data.get("max_stress_level"),
            data.get("stress_qualifier"),
        )

    async def upsert_heart_rate_samples(self, user_id: int, samples: List[Dict[str, Any]]) -> int:
        """Batch upsert heart rate samples.

        Args:
            user_id: User ID
            samples: List of heart rate samples

        Returns:
            Number of samples inserted/updated
        """
        if not samples:
            return 0

        query = """
            INSERT INTO heart_rate_samples (user_id, timestamp, heart_rate)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, timestamp) DO UPDATE
            SET heart_rate = EXCLUDED.heart_rate
        """
        records = [
            (user_id, sample.get("timestamp"), sample.get("heart_rate"))
            for sample in samples
        ]
        await self.pool.executemany(query, records)
        return len(records)

    async def upsert_sleep_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert sleep data.

        Args:
            user_id: User ID
            data: Sleep data
        """
        query = """
            INSERT INTO sleep_data (
                user_id, calendar_date, sleep_start_timestamp, sleep_end_timestamp,
                total_sleep_seconds, deep_sleep_seconds, light_sleep_seconds, rem_sleep_seconds,
                awake_seconds, sleep_score, sleep_quality, sleep_levels
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                sleep_start_timestamp = EXCLUDED.sleep_start_timestamp,
                sleep_end_timestamp = EXCLUDED.sleep_end_timestamp,
                total_sleep_seconds = EXCLUDED.total_sleep_seconds,
                deep_sleep_seconds = EXCLUDED.deep_sleep_seconds,
                light_sleep_seconds = EXCLUDED.light_sleep_seconds,
                rem_sleep_seconds = EXCLUDED.rem_sleep_seconds,
                awake_seconds = EXCLUDED.awake_seconds,
                sleep_score = EXCLUDED.sleep_score,
                sleep_quality = EXCLUDED.sleep_quality,
                sleep_levels = EXCLUDED.sleep_levels,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("sleep_start_timestamp"),
            data.get("sleep_end_timestamp"),
            data.get("total_sleep_seconds"),
            data.get("deep_sleep_seconds"),
            data.get("light_sleep_seconds"),
            data.get("rem_sleep_seconds"),
            data.get("awake_seconds"),
            data.get("sleep_score"),
            data.get("sleep_quality"),
            data.get("sleep_levels"),
        )

    async def upsert_stress_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert stress data.

        Args:
            user_id: User ID
            data: Stress data
        """
        query = """
            INSERT INTO stress_data (
                user_id, calendar_date, average_stress_level, max_stress_level,
                rest_stress_duration_seconds, activity_stress_duration_seconds,
                uncategorized_stress_duration_seconds, low_stress_duration_seconds,
                medium_stress_duration_seconds, high_stress_duration_seconds, stress_chart_values
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                average_stress_level = EXCLUDED.average_stress_level,
                max_stress_level = EXCLUDED.max_stress_level,
                rest_stress_duration_seconds = EXCLUDED.rest_stress_duration_seconds,
                activity_stress_duration_seconds = EXCLUDED.activity_stress_duration_seconds,
                uncategorized_stress_duration_seconds = EXCLUDED.uncategorized_stress_duration_seconds,
                low_stress_duration_seconds = EXCLUDED.low_stress_duration_seconds,
                medium_stress_duration_seconds = EXCLUDED.medium_stress_duration_seconds,
                high_stress_duration_seconds = EXCLUDED.high_stress_duration_seconds,
                stress_chart_values = EXCLUDED.stress_chart_values,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("average_stress_level"),
            data.get("max_stress_level"),
            data.get("rest_stress_duration_seconds"),
            data.get("activity_stress_duration_seconds"),
            data.get("uncategorized_stress_duration_seconds"),
            data.get("low_stress_duration_seconds"),
            data.get("medium_stress_duration_seconds"),
            data.get("high_stress_duration_seconds"),
            data.get("stress_chart_values"),
        )

    async def upsert_body_battery(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert body battery data.

        Args:
            user_id: User ID
            data: Body battery data
        """
        query = """
            INSERT INTO body_battery (
                user_id, calendar_date, charged_value, drained_value, highest_value,
                lowest_value, start_timestamp, end_timestamp, body_battery_values
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                charged_value = EXCLUDED.charged_value,
                drained_value = EXCLUDED.drained_value,
                highest_value = EXCLUDED.highest_value,
                lowest_value = EXCLUDED.lowest_value,
                start_timestamp = EXCLUDED.start_timestamp,
                end_timestamp = EXCLUDED.end_timestamp,
                body_battery_values = EXCLUDED.body_battery_values,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("charged_value"),
            data.get("drained_value"),
            data.get("highest_value"),
            data.get("lowest_value"),
            data.get("start_timestamp"),
            data.get("end_timestamp"),
            data.get("body_battery_values"),
        )

    # ============================================
    # Body Composition Operations
    # ============================================

    async def upsert_body_composition(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert body composition data.

        Args:
            user_id: User ID
            data: Body composition data
        """
        query = """
            INSERT INTO body_composition (
                user_id, timestamp, weight_kg, bmi, body_fat_percentage, body_water_percentage,
                bone_mass_kg, muscle_mass_kg, metabolic_age, visceral_fat_rating,
                basal_met, active_met, physique_rating, source_type
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (user_id, timestamp) DO UPDATE SET
                weight_kg = EXCLUDED.weight_kg,
                bmi = EXCLUDED.bmi,
                body_fat_percentage = EXCLUDED.body_fat_percentage,
                body_water_percentage = EXCLUDED.body_water_percentage,
                bone_mass_kg = EXCLUDED.bone_mass_kg,
                muscle_mass_kg = EXCLUDED.muscle_mass_kg,
                metabolic_age = EXCLUDED.metabolic_age,
                visceral_fat_rating = EXCLUDED.visceral_fat_rating,
                basal_met = EXCLUDED.basal_met,
                active_met = EXCLUDED.active_met,
                physique_rating = EXCLUDED.physique_rating,
                source_type = EXCLUDED.source_type,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("timestamp"),
            data.get("weight_kg"),
            data.get("bmi"),
            data.get("body_fat_percentage"),
            data.get("body_water_percentage"),
            data.get("bone_mass_kg"),
            data.get("muscle_mass_kg"),
            data.get("metabolic_age"),
            data.get("visceral_fat_rating"),
            data.get("basal_met"),
            data.get("active_met"),
            data.get("physique_rating"),
            data.get("source_type"),
        )

    # ============================================
    # Advanced Metrics Operations
    # ============================================

    async def upsert_hrv_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert HRV data."""
        query = """
            INSERT INTO hrv_data (
                user_id, calendar_date, weekly_avg, last_night_avg, last_night_5_min_high,
                hrv_status, feedback_phrase
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                weekly_avg = EXCLUDED.weekly_avg,
                last_night_avg = EXCLUDED.last_night_avg,
                last_night_5_min_high = EXCLUDED.last_night_5_min_high,
                hrv_status = EXCLUDED.hrv_status,
                feedback_phrase = EXCLUDED.feedback_phrase,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("weekly_avg"),
            data.get("last_night_avg"),
            data.get("last_night_5_min_high"),
            data.get("hrv_status"),
            data.get("feedback_phrase"),
        )

    async def upsert_spo2_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert SpO2 data."""
        query = """
            INSERT INTO spo2_data (
                user_id, calendar_date, average_spo2_percentage, lowest_spo2_percentage,
                latest_spo2_reading, latest_spo2_reading_timestamp, spo2_values
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                average_spo2_percentage = EXCLUDED.average_spo2_percentage,
                lowest_spo2_percentage = EXCLUDED.lowest_spo2_percentage,
                latest_spo2_reading = EXCLUDED.latest_spo2_reading,
                latest_spo2_reading_timestamp = EXCLUDED.latest_spo2_reading_timestamp,
                spo2_values = EXCLUDED.spo2_values,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("average_spo2_percentage"),
            data.get("lowest_spo2_percentage"),
            data.get("latest_spo2_reading"),
            data.get("latest_spo2_reading_timestamp"),
            data.get("spo2_values"),
        )

    async def upsert_fitness_metrics(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert fitness metrics."""
        query = """
            INSERT INTO fitness_metrics (
                user_id, calendar_date, vo2_max, vo2_max_running, vo2_max_cycling,
                fitness_age, lactate_threshold_bpm, lactate_threshold_speed
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                vo2_max = EXCLUDED.vo2_max,
                vo2_max_running = EXCLUDED.vo2_max_running,
                vo2_max_cycling = EXCLUDED.vo2_max_cycling,
                fitness_age = EXCLUDED.fitness_age,
                lactate_threshold_bpm = EXCLUDED.lactate_threshold_bpm,
                lactate_threshold_speed = EXCLUDED.lactate_threshold_speed,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("vo2_max"),
            data.get("vo2_max_running"),
            data.get("vo2_max_cycling"),
            data.get("fitness_age"),
            data.get("lactate_threshold_bpm"),
            data.get("lactate_threshold_speed"),
        )

    async def upsert_respiration_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert respiration data."""
        query = """
            INSERT INTO respiration_data (
                user_id, calendar_date, avg_waking_respiration_rate, max_waking_respiration_rate,
                min_waking_respiration_rate, avg_sleep_respiration_rate
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                avg_waking_respiration_rate = EXCLUDED.avg_waking_respiration_rate,
                max_waking_respiration_rate = EXCLUDED.max_waking_respiration_rate,
                min_waking_respiration_rate = EXCLUDED.min_waking_respiration_rate,
                avg_sleep_respiration_rate = EXCLUDED.avg_sleep_respiration_rate,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("avg_waking_respiration_rate"),
            data.get("max_waking_respiration_rate"),
            data.get("min_waking_respiration_rate"),
            data.get("avg_sleep_respiration_rate"),
        )

    # ============================================
    # Activity Operations
    # ============================================

    async def upsert_activity(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert activity data."""
        query = """
            INSERT INTO activities (
                user_id, activity_id, activity_name, activity_type, sport_type, start_timestamp,
                duration_seconds, distance_meters, average_speed, max_speed, average_pace, max_pace,
                calories, average_hr, max_hr, average_running_cadence, max_running_cadence,
                average_bike_cadence, max_bike_cadence, average_power, max_power, normalized_power,
                training_stress_score, intensity_factor, elevation_gain_meters, elevation_loss_meters,
                min_elevation_meters, max_elevation_meters, average_temperature, max_temperature, min_temperature,
                training_effect, aerobic_training_effect, anaerobic_training_effect,
                avg_vertical_oscillation, avg_ground_contact_time, avg_stride_length,
                vo2_max_value, lactate_threshold_bpm, device_name, description,
                manual_activity, pr, favorite, auto_calc_calories, num_laps, activity_data
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, $38,
                $39, $40, $41, $42, $43, $44, $45, $46, $47
            )
            ON CONFLICT (activity_id) DO UPDATE SET
                activity_name = EXCLUDED.activity_name,
                activity_type = EXCLUDED.activity_type,
                sport_type = EXCLUDED.sport_type,
                start_timestamp = EXCLUDED.start_timestamp,
                duration_seconds = EXCLUDED.duration_seconds,
                distance_meters = EXCLUDED.distance_meters,
                average_speed = EXCLUDED.average_speed,
                max_speed = EXCLUDED.max_speed,
                average_pace = EXCLUDED.average_pace,
                max_pace = EXCLUDED.max_pace,
                calories = EXCLUDED.calories,
                average_hr = EXCLUDED.average_hr,
                max_hr = EXCLUDED.max_hr,
                average_running_cadence = EXCLUDED.average_running_cadence,
                max_running_cadence = EXCLUDED.max_running_cadence,
                average_bike_cadence = EXCLUDED.average_bike_cadence,
                max_bike_cadence = EXCLUDED.max_bike_cadence,
                average_power = EXCLUDED.average_power,
                max_power = EXCLUDED.max_power,
                normalized_power = EXCLUDED.normalized_power,
                training_stress_score = EXCLUDED.training_stress_score,
                intensity_factor = EXCLUDED.intensity_factor,
                elevation_gain_meters = EXCLUDED.elevation_gain_meters,
                elevation_loss_meters = EXCLUDED.elevation_loss_meters,
                min_elevation_meters = EXCLUDED.min_elevation_meters,
                max_elevation_meters = EXCLUDED.max_elevation_meters,
                average_temperature = EXCLUDED.average_temperature,
                max_temperature = EXCLUDED.max_temperature,
                min_temperature = EXCLUDED.min_temperature,
                training_effect = EXCLUDED.training_effect,
                aerobic_training_effect = EXCLUDED.aerobic_training_effect,
                anaerobic_training_effect = EXCLUDED.anaerobic_training_effect,
                avg_vertical_oscillation = EXCLUDED.avg_vertical_oscillation,
                avg_ground_contact_time = EXCLUDED.avg_ground_contact_time,
                avg_stride_length = EXCLUDED.avg_stride_length,
                vo2_max_value = EXCLUDED.vo2_max_value,
                lactate_threshold_bpm = EXCLUDED.lactate_threshold_bpm,
                device_name = EXCLUDED.device_name,
                description = EXCLUDED.description,
                manual_activity = EXCLUDED.manual_activity,
                pr = EXCLUDED.pr,
                favorite = EXCLUDED.favorite,
                auto_calc_calories = EXCLUDED.auto_calc_calories,
                num_laps = EXCLUDED.num_laps,
                activity_data = EXCLUDED.activity_data,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(query, user_id, *[data.get(k) for k in [
            "activity_id", "activity_name", "activity_type", "sport_type", "start_timestamp",
            "duration_seconds", "distance_meters", "average_speed", "max_speed", "average_pace", "max_pace",
            "calories", "average_hr", "max_hr", "average_running_cadence", "max_running_cadence",
            "average_bike_cadence", "max_bike_cadence", "average_power", "max_power", "normalized_power",
            "training_stress_score", "intensity_factor", "elevation_gain_meters", "elevation_loss_meters",
            "min_elevation_meters", "max_elevation_meters", "average_temperature", "max_temperature", "min_temperature",
            "training_effect", "aerobic_training_effect", "anaerobic_training_effect",
            "avg_vertical_oscillation", "avg_ground_contact_time", "avg_stride_length",
            "vo2_max_value", "lactate_threshold_bpm", "device_name", "description",
            "manual_activity", "pr", "favorite", "auto_calc_calories", "num_laps", "activity_data"
        ]])

    async def upsert_hydration_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Upsert hydration data."""
        query = """
            INSERT INTO hydration_data (
                user_id, calendar_date, total_hydration_ml, hydration_goal_ml, hydration_entries
            )
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                total_hydration_ml = EXCLUDED.total_hydration_ml,
                hydration_goal_ml = EXCLUDED.hydration_goal_ml,
                hydration_entries = EXCLUDED.hydration_entries,
                updated_at = CURRENT_TIMESTAMP
        """
        await self.pool.execute(
            query,
            user_id,
            data.get("calendar_date"),
            data.get("total_hydration_ml"),
            data.get("hydration_goal_ml"),
            data.get("hydration_entries"),
        )
