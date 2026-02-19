"""Pydantic response schemas."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class Pagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class Page(BaseModel, Generic[T]):
    data: List[T]
    pagination: Pagination


class HealthResponse(BaseModel):
    status: str


class DailySummary(BaseModel):
    calendar_date: date
    total_steps: Optional[int] = None
    step_goal: Optional[int] = None
    total_distance_meters: Optional[float] = None
    active_calories: Optional[int] = None
    bmr_calories: Optional[int] = None
    total_calories: Optional[int] = None
    floors_ascended: Optional[float] = None
    floors_descended: Optional[float] = None
    moderate_intensity_minutes: Optional[int] = None
    vigorous_intensity_minutes: Optional[int] = None
    highly_active_seconds: Optional[int] = None
    active_seconds: Optional[int] = None
    sedentary_seconds: Optional[int] = None
    sleeping_seconds: Optional[int] = None
    max_heart_rate: Optional[int] = None
    min_heart_rate: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    average_heart_rate: Optional[int] = None
    average_stress_level: Optional[int] = None
    max_stress_level: Optional[int] = None
    stress_qualifier: Optional[str] = None

    model_config = {"from_attributes": True}


class HeartRateSample(BaseModel):
    timestamp: datetime
    heart_rate: Optional[int] = None

    model_config = {"from_attributes": True}


class SleepData(BaseModel):
    calendar_date: date
    sleep_start_timestamp: Optional[datetime] = None
    sleep_end_timestamp: Optional[datetime] = None
    total_sleep_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    light_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None
    awake_seconds: Optional[int] = None
    sleep_score: Optional[int] = None
    sleep_quality: Optional[str] = None

    model_config = {"from_attributes": True}


class StressData(BaseModel):
    calendar_date: date
    average_stress_level: Optional[int] = None
    max_stress_level: Optional[int] = None
    rest_stress_duration_seconds: Optional[int] = None
    activity_stress_duration_seconds: Optional[int] = None
    low_stress_duration_seconds: Optional[int] = None
    medium_stress_duration_seconds: Optional[int] = None
    high_stress_duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


class BodyBattery(BaseModel):
    calendar_date: date
    charged_value: Optional[int] = None
    drained_value: Optional[int] = None
    highest_value: Optional[int] = None
    lowest_value: Optional[int] = None

    model_config = {"from_attributes": True}


class BodyComposition(BaseModel):
    timestamp: datetime
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    body_water_percentage: Optional[float] = None
    bone_mass_kg: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    metabolic_age: Optional[int] = None
    visceral_fat_rating: Optional[int] = None

    model_config = {"from_attributes": True}


class HrvData(BaseModel):
    calendar_date: date
    weekly_avg: Optional[int] = None
    last_night_avg: Optional[int] = None
    last_night_5_min_high: Optional[int] = None
    hrv_status: Optional[str] = None
    feedback_phrase: Optional[str] = None

    model_config = {"from_attributes": True}


class Spo2Data(BaseModel):
    calendar_date: date
    average_spo2_percentage: Optional[float] = None
    lowest_spo2_percentage: Optional[float] = None
    latest_spo2_reading: Optional[float] = None

    model_config = {"from_attributes": True}


class FitnessMetrics(BaseModel):
    calendar_date: date
    vo2_max: Optional[float] = None
    vo2_max_running: Optional[float] = None
    vo2_max_cycling: Optional[float] = None
    fitness_age: Optional[int] = None
    lactate_threshold_bpm: Optional[int] = None
    lactate_threshold_speed: Optional[float] = None

    model_config = {"from_attributes": True}


class RespirationData(BaseModel):
    calendar_date: date
    avg_waking_respiration_rate: Optional[float] = None
    max_waking_respiration_rate: Optional[float] = None
    min_waking_respiration_rate: Optional[float] = None
    avg_sleep_respiration_rate: Optional[float] = None

    model_config = {"from_attributes": True}


class TrainingReadiness(BaseModel):
    calendar_date: date
    score: Optional[int] = None
    score_feedback: Optional[str] = None
    hrv_status: Optional[str] = None
    sleep_score: Optional[int] = None
    recent_training_load: Optional[int] = None
    acute_load: Optional[float] = None
    chronic_load: Optional[float] = None

    model_config = {"from_attributes": True}


class ActivityUpdate(BaseModel):
    custom_name: Optional[str] = None


class Activity(BaseModel):
    activity_id: int
    activity_name: Optional[str] = None
    custom_name: Optional[str] = None
    activity_type: Optional[str] = None
    sport_type: Optional[str] = None
    start_timestamp: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    distance_meters: Optional[float] = None
    average_speed: Optional[float] = None
    max_speed: Optional[float] = None
    calories: Optional[int] = None
    average_hr: Optional[int] = None
    max_hr: Optional[int] = None
    elevation_gain_meters: Optional[float] = None
    elevation_loss_meters: Optional[float] = None
    training_stress_score: Optional[float] = None
    vo2_max_value: Optional[float] = None
    device_name: Optional[str] = None
    num_laps: Optional[int] = None
    aerobic_training_effect: Optional[float] = None
    anaerobic_training_effect: Optional[float] = None

    model_config = {"from_attributes": True}


class ActivityDetail(Activity):
    average_pace: Optional[float] = None
    max_pace: Optional[float] = None
    average_running_cadence: Optional[float] = None
    max_running_cadence: Optional[float] = None
    average_bike_cadence: Optional[float] = None
    max_bike_cadence: Optional[float] = None
    average_power: Optional[float] = None
    max_power: Optional[float] = None
    normalized_power: Optional[float] = None
    intensity_factor: Optional[float] = None
    min_elevation_meters: Optional[float] = None
    max_elevation_meters: Optional[float] = None
    average_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    min_temperature: Optional[float] = None
    training_effect: Optional[float] = None
    aerobic_training_effect: Optional[float] = None
    anaerobic_training_effect: Optional[float] = None
    avg_vertical_oscillation: Optional[float] = None
    avg_ground_contact_time: Optional[float] = None
    avg_stride_length: Optional[float] = None
    lactate_threshold_bpm: Optional[int] = None
    description: Optional[str] = None
    manual_activity: Optional[bool] = None
    pr: Optional[bool] = None
    favorite: Optional[bool] = None

    model_config = {"from_attributes": True}


class ActivitySplit(BaseModel):
    split_index: Optional[int] = None
    split_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    distance_meters: Optional[float] = None
    average_speed: Optional[float] = None
    average_hr: Optional[int] = None
    calories: Optional[int] = None
    elevation_gain: Optional[float] = None

    model_config = {"from_attributes": True}


class HydrationData(BaseModel):
    calendar_date: date
    total_hydration_ml: Optional[float] = None
    hydration_goal_ml: Optional[float] = None

    model_config = {"from_attributes": True}


VALID_SPORT_TYPES = {"running", "trail_running", "cycling", "swimming", "strength_training", "rest", "stretching"}
VALID_INTENSITIES = {"easy", "moderate", "hard", "race"}


class PlannedWorkoutCreate(BaseModel):
    planned_date: date
    sport_type: str
    title: str
    description: Optional[str] = None
    planned_duration_seconds: Optional[int] = None
    planned_distance_meters: Optional[float] = None
    intensity: str = "moderate"


class PlannedWorkoutUpdate(BaseModel):
    planned_date: Optional[date] = None
    sport_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    planned_duration_seconds: Optional[int] = None
    planned_distance_meters: Optional[float] = None
    intensity: Optional[str] = None
    completed: Optional[bool] = None


class PlannedWorkout(BaseModel):
    id: int
    user_id: int
    planned_date: date
    sport_type: str
    title: str
    description: Optional[str] = None
    planned_duration_seconds: Optional[int] = None
    planned_distance_meters: Optional[float] = None
    intensity: str = "moderate"
    completed: bool = False
    created_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BulkImportResult(BaseModel):
    imported: int
    errors: List[str] = []


class SyncStatus(BaseModel):
    category: str
    last_sync_date: Optional[date] = None
    last_sync_timestamp: Optional[datetime] = None
    records_synced: Optional[int] = None
    sync_status: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class SyncTriggerRequest(BaseModel):
    categories: Optional[List[str]] = Field(
        None,
        description="Categories to sync. Defaults to all.",
        json_schema_extra={"examples": [["daily_health", "activities"]]},
    )
    mode: str = Field(
        "incremental",
        description="Sync mode: 'incremental' or 'full'",
    )
    days_back: int = Field(90, description="Days to look back for full sync")
    start_date: Optional[date] = Field(None, description="Override start date")
    end_date: Optional[date] = Field(None, description="Override end date")
    dry_run: bool = Field(False, description="If true, show what would be synced without writing")
    better_auth_user_id: Optional[str] = Field(None, description="Better-Auth user ID to sync for")


class SyncJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class SyncJobResponse(BaseModel):
    job_id: str
    status: SyncJobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    request: SyncTriggerRequest
    result: Optional[dict] = None
    error: Optional[str] = None
    logs: List[str] = []


class SyncTriggerResponse(BaseModel):
    job_id: str
    message: str


# Coaching
class InviteCodeCreate(BaseModel):
    pass  # code is auto-generated


class InviteCodeResponse(BaseModel):
    id: int
    code: str
    coach_better_auth_id: str
    status: str
    redeemed_by_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    redeemed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RedeemCodeRequest(BaseModel):
    code: str


class CoachAthlete(BaseModel):
    athlete_user_id: int
    display_name: Optional[str] = None
    email: Optional[str] = None
    status: str
    linked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CoachInfo(BaseModel):
    coach_better_auth_id: str
    coach_name: Optional[str] = None
    coach_email: Optional[str] = None
    status: str
    linked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CoachingStatus(BaseModel):
    coaching_enabled: bool
    athletes: List[CoachAthlete] = []
    coaches: List[CoachInfo] = []


def make_page(rows, total: int, limit: int, offset: int, schema_class) -> dict:
    return {
        "data": [schema_class.model_validate(dict(r)) for r in rows],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(rows) < total,
        },
    }
