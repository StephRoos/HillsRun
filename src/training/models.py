"""Pure Pydantic models and enums for the training plan engine."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ExperienceLevel(str, Enum):
    """Athlete experience level."""

    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class RaceObjective(str, Enum):
    """Race finish objective."""

    finish = "finish"
    midpack = "midpack"
    performance = "performance"


class RaceCategory(str, Enum):
    """Trail race distance category."""

    trail_court = "trail_court"  # < 42 km
    trail_moyen = "trail_moyen"  # 42-80 km
    ultra = "ultra"  # 80-160 km
    ultra_longue = "ultra_longue"  # > 160 km


class PlanPhase(str, Enum):
    """Training plan periodization phase."""

    base = "base"
    development = "development"
    specific = "specific"
    taper = "taper"


class SessionType(str, Enum):
    """Workout session type."""

    EF = "EF"  # Endurance fondamentale
    SL = "SL"  # Sortie longue
    TMP = "TMP"  # Tempo / seuil
    INT = "INT"  # Intervalles
    COT = "COT"  # Cotes (hill repeats)
    DESC = "DESC"  # Descente technique
    REC = "REC"  # Recuperation
    RMU = "RMU"  # Renforcement musculaire
    REST = "REST"  # Jour de repos


class Intensity(str, Enum):
    """Session intensity level."""

    easy = "easy"
    moderate = "moderate"
    hard = "hard"
    race = "race"


class HRZone(BaseModel):
    """Heart rate training zone."""

    zone: int
    name: str
    hr_min: int
    hr_max: int
    description: str


class WorkoutBlock(BaseModel):
    """Single block within a structured workout."""

    name: str
    duration_seconds: int
    hr_zone: Optional[int] = None
    description: str = ""


class UserFitnessData(BaseModel):
    """Aggregated fitness snapshot from Garmin data."""

    vo2_max: Optional[float] = None
    resting_hr: Optional[int] = None
    max_hr: Optional[int] = None
    weight_kg: Optional[float] = None
    vma_kmh: Optional[float] = None
    weekly_volume_km: Optional[float] = None
    weekly_elevation_m: Optional[int] = None
    avg_training_readiness: Optional[float] = None
    chronic_load: Optional[float] = None
    acute_load: Optional[float] = None
    recent_long_run_km: Optional[float] = None
    recent_long_run_duration_s: Optional[int] = None
    avg_sleep_score: Optional[float] = None
    avg_hrv: Optional[float] = None


class RaceTargetInput(BaseModel):
    """Input data for a target race."""

    race_name: str
    race_date: date
    distance_km: float = Field(gt=0)
    elevation_gain_m: int = Field(default=0, ge=0)
    elevation_loss_m: int = Field(default=0, ge=0)
    altitude_min_m: int = Field(default=0, ge=0)
    altitude_max_m: int = Field(default=0, ge=0)
    technical_percent: int = Field(default=0, ge=0, le=100)
    cutoff_hours: Optional[float] = None
    itra_points: Optional[int] = None
    objective: RaceObjective = RaceObjective.finish


class DayPreferences(BaseModel):
    """Preferred days for each session category.

    Day numbers follow ISO convention: 1=Monday, 7=Sunday.
    """

    long_run: Optional[int] = Field(default=None, ge=1, le=7)
    quality: Optional[list[int]] = None
    strength: Optional[list[int]] = None
    easy_run: Optional[list[int]] = None

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """Ensure quality days are valid (1-7) and max 3 entries."""
        if v is None:
            return v
        if len(v) > 3:
            raise ValueError("quality must have at most 3 days")
        if not all(1 <= d <= 7 for d in v):
            raise ValueError("quality days must be between 1 and 7")
        return v

    @field_validator("strength")
    @classmethod
    def validate_strength(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """Ensure strength days are valid (1-7) and max 2 entries."""
        if v is None:
            return v
        if len(v) > 2:
            raise ValueError("strength must have at most 2 days")
        if not all(1 <= d <= 7 for d in v):
            raise ValueError("strength days must be between 1 and 7")
        return v

    @field_validator("easy_run")
    @classmethod
    def validate_easy_run(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """Ensure easy_run days are valid (1-7) and max 5 entries."""
        if v is None:
            return v
        if len(v) > 5:
            raise ValueError("easy_run must have at most 5 days")
        if not all(1 <= d <= 7 for d in v):
            raise ValueError("easy_run days must be between 1 and 7")
        return v


class GeneratePlanRequest(BaseModel):
    """Request to generate a training plan."""

    race_target_id: int
    plan_name: Optional[str] = None
    total_weeks: Optional[int] = Field(default=None, ge=6, le=30)
    start_date: Optional[date] = None
    day_preferences: Optional[DayPreferences] = None


class RaceFlags(BaseModel):
    """Flags derived from race classification."""

    category: RaceCategory
    high_dplus: bool = False
    technical: bool = False
    is_ultra: bool = False
    high_altitude: bool = False


class WeekSpec(BaseModel):
    """Specification for a single training week."""

    week_number: int
    phase: PlanPhase
    is_recovery_week: bool = False


class SessionSpec(BaseModel):
    """Specification for a single training session."""

    day_of_week: int = Field(ge=1, le=7)
    session_type: SessionType
    title: str
    description: str = ""
    sport_type: str = "trail_running"
    target_duration_seconds: Optional[int] = None
    target_distance_meters: Optional[float] = None
    target_elevation_gain_m: Optional[int] = None
    target_tss: Optional[float] = None
    hr_zone_primary: Optional[int] = None
    intensity: Intensity = Intensity.moderate
    blocks: list[WorkoutBlock] = []
    sort_order: int = 0
