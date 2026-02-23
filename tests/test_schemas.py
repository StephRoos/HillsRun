"""Tests for Pydantic schemas."""

import pytest
from datetime import date, datetime

from src.api.schemas import (
    DailySummary,
    HeartRateSample,
    SleepData,
    StressData,
    BodyBattery,
    BodyComposition,
    HrvData,
    Spo2Data,
    FitnessMetrics,
    RespirationData,
    TrainingReadiness,
    Activity,
    ActivityDetail,
    ActivitySplit,
    HydrationData,
    PlannedWorkoutCreate,
    PlannedWorkout,
    make_page,
    Pagination,
)


class TestDailySummary:
    """Tests for DailySummary schema."""

    def test_daily_summary_minimal(self):
        """Test creating DailySummary with only required field."""
        summary = DailySummary(calendar_date=date(2025, 1, 1))
        assert summary.calendar_date == date(2025, 1, 1)
        assert summary.total_steps is None

    def test_daily_summary_with_data(self):
        """Test creating DailySummary with full data."""
        summary = DailySummary(
            calendar_date=date(2025, 1, 1),
            total_steps=10000,
            step_goal=12000,
            total_calories=2500,
            max_heart_rate=150,
            min_heart_rate=50,
            average_stress_level=30,
        )
        assert summary.total_steps == 10000
        assert summary.step_goal == 12000
        assert summary.total_calories == 2500
        assert summary.max_heart_rate == 150

    def test_daily_summary_from_dict(self):
        """Test creating DailySummary from dict."""
        data = {
            "calendar_date": date(2025, 1, 1),
            "total_steps": 8500,
            "step_goal": 10000,
        }
        summary = DailySummary.model_validate(data)
        assert summary.total_steps == 8500


class TestHeartRateSample:
    """Tests for HeartRateSample schema."""

    def test_heart_rate_sample(self):
        """Test creating HeartRateSample."""
        timestamp = datetime(2025, 1, 1, 12, 30, 0)
        sample = HeartRateSample(timestamp=timestamp, heart_rate=75)
        assert sample.timestamp == timestamp
        assert sample.heart_rate == 75

    def test_heart_rate_sample_no_value(self):
        """Test HeartRateSample without heart_rate value."""
        timestamp = datetime(2025, 1, 1, 12, 30, 0)
        sample = HeartRateSample(timestamp=timestamp)
        assert sample.heart_rate is None


class TestSleepData:
    """Tests for SleepData schema."""

    def test_sleep_data_minimal(self):
        """Test creating SleepData with minimal data."""
        sleep = SleepData(calendar_date=date(2025, 1, 1))
        assert sleep.calendar_date == date(2025, 1, 1)
        assert sleep.total_sleep_seconds is None

    def test_sleep_data_with_stages(self):
        """Test creating SleepData with sleep stages."""
        sleep = SleepData(
            calendar_date=date(2025, 1, 1),
            deep_sleep_seconds=3600,
            light_sleep_seconds=14400,
            rem_sleep_seconds=7200,
            sleep_score=85,
        )
        assert sleep.deep_sleep_seconds == 3600
        assert sleep.sleep_score == 85


class TestStressData:
    """Tests for StressData schema."""

    def test_stress_data(self):
        """Test creating StressData."""
        stress = StressData(
            calendar_date=date(2025, 1, 1),
            average_stress_level=35,
            max_stress_level=60,
        )
        assert stress.average_stress_level == 35
        assert stress.max_stress_level == 60


class TestBodyBattery:
    """Tests for BodyBattery schema."""

    def test_body_battery(self):
        """Test creating BodyBattery."""
        bb = BodyBattery(
            calendar_date=date(2025, 1, 1),
            charged_value=30,
            drained_value=25,
            highest_value=100,
            lowest_value=45,
        )
        assert bb.charged_value == 30
        assert bb.highest_value == 100


class TestBodyComposition:
    """Tests for BodyComposition schema."""

    def test_body_composition(self):
        """Test creating BodyComposition."""
        timestamp = datetime(2025, 1, 1, 8, 0, 0)
        comp = BodyComposition(
            timestamp=timestamp,
            weight_kg=75.5,
            bmi=24.2,
            body_fat_percentage=15.5,
            muscle_mass_kg=62.0,
        )
        assert comp.weight_kg == 75.5
        assert comp.bmi == 24.2


class TestHrvData:
    """Tests for HrvData schema."""

    def test_hrv_data(self):
        """Test creating HrvData."""
        hrv = HrvData(
            calendar_date=date(2025, 1, 1),
            weekly_avg=45,
            last_night_avg=50,
            hrv_status="balanced",
        )
        assert hrv.weekly_avg == 45
        assert hrv.hrv_status == "balanced"


class TestSpo2Data:
    """Tests for Spo2Data schema."""

    def test_spo2_data(self):
        """Test creating Spo2Data."""
        spo2 = Spo2Data(
            calendar_date=date(2025, 1, 1),
            average_spo2_percentage=97.5,
            lowest_spo2_percentage=94.0,
            latest_spo2_reading=98.0,
        )
        assert spo2.average_spo2_percentage == 97.5


class TestFitnessMetrics:
    """Tests for FitnessMetrics schema."""

    def test_fitness_metrics(self):
        """Test creating FitnessMetrics."""
        metrics = FitnessMetrics(
            calendar_date=date(2025, 1, 1),
            vo2_max=55.0,
            vo2_max_running=52.0,
            fitness_age=25,
            lactate_threshold_bpm=170,
        )
        assert metrics.vo2_max == 55.0
        assert metrics.fitness_age == 25


class TestRespirationData:
    """Tests for RespirationData schema."""

    def test_respiration_data(self):
        """Test creating RespirationData."""
        resp = RespirationData(
            calendar_date=date(2025, 1, 1),
            avg_waking_respiration_rate=16.5,
            avg_sleep_respiration_rate=14.2,
        )
        assert resp.avg_waking_respiration_rate == 16.5


class TestTrainingReadiness:
    """Tests for TrainingReadiness schema."""

    def test_training_readiness(self):
        """Test creating TrainingReadiness."""
        readiness = TrainingReadiness(
            calendar_date=date(2025, 1, 1),
            score=75,
            sleep_score=80,
            recent_training_load=200,
            acute_load=150.5,
        )
        assert readiness.score == 75
        assert readiness.acute_load == 150.5


class TestActivity:
    """Tests for Activity schema."""

    def test_activity_minimal(self):
        """Test creating Activity with minimal data."""
        activity = Activity(activity_id=12345)
        assert activity.activity_id == 12345

    def test_activity_with_data(self):
        """Test creating Activity with full data."""
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        activity = Activity(
            activity_id=12345,
            activity_name="Morning Run",
            custom_name="Fast 5K",
            activity_type="running",
            sport_type="running",
            start_timestamp=start_time,
            duration_seconds=1800,
            distance_meters=5000,
            average_speed=2.78,
            calories=600,
            average_hr=150,
            max_hr=170,
            elevation_gain_meters=100,
        )
        assert activity.activity_name == "Morning Run"
        assert activity.distance_meters == 5000
        assert activity.average_hr == 150


class TestActivityDetail:
    """Tests for ActivityDetail schema."""

    def test_activity_detail(self):
        """Test creating ActivityDetail with extended fields."""
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        detail = ActivityDetail(
            activity_id=12345,
            activity_name="Trail Run",
            duration_seconds=3600,
            distance_meters=10000,
            average_pace=6.0,
            max_pace=5.5,
            average_running_cadence=170,
            max_elevation_meters=500,
            min_elevation_meters=100,
            average_temperature=15.5,
            description="Great run on the trail",
        )
        assert detail.activity_id == 12345
        assert detail.average_pace == 6.0
        assert detail.description == "Great run on the trail"


class TestActivitySplit:
    """Tests for ActivitySplit schema."""

    def test_activity_split(self):
        """Test creating ActivitySplit."""
        split = ActivitySplit(
            split_index=1,
            split_type="lap",
            duration_seconds=600,
            distance_meters=1000,
            average_speed=1.67,
            average_hr=150,
            calories=100,
        )
        assert split.split_index == 1
        assert split.distance_meters == 1000


class TestHydrationData:
    """Tests for HydrationData schema."""

    def test_hydration_data(self):
        """Test creating HydrationData."""
        hydration = HydrationData(
            calendar_date=date(2025, 1, 1),
            total_hydration_ml=2500,
            hydration_goal_ml=3000,
        )
        assert hydration.total_hydration_ml == 2500


class TestPlannedWorkoutCreate:
    """Tests for PlannedWorkoutCreate schema."""

    def test_planned_workout_create(self):
        """Test creating PlannedWorkoutCreate."""
        workout = PlannedWorkoutCreate(
            planned_date=date(2025, 1, 2),
            sport_type="running",
            title="Long Run",
            description="Easy pace",
            planned_duration_seconds=5400,
            planned_distance_meters=10000,
            intensity="easy",
        )
        assert workout.planned_date == date(2025, 1, 2)
        assert workout.sport_type == "running"
        assert workout.intensity == "easy"


class TestPlannedWorkout:
    """Tests for PlannedWorkout schema."""

    def test_planned_workout(self):
        """Test creating PlannedWorkout."""
        now = datetime.now()
        workout = PlannedWorkout(
            id=1,
            user_id=123,
            planned_date=date(2025, 1, 2),
            sport_type="running",
            title="Long Run",
            intensity="moderate",
            completed=False,
            created_at=now,
        )
        assert workout.id == 1
        assert workout.completed is False


class TestMakePage:
    """Tests for make_page helper function."""

    def test_make_page_empty_results(self):
        """Test make_page with empty results."""
        result = make_page([], 0, 50, 0, DailySummary)
        assert result["data"] == []
        assert result["pagination"]["total"] == 0
        assert result["pagination"]["has_more"] is False

    def test_make_page_with_data(self):
        """Test make_page with data."""
        rows = [
            {"calendar_date": date(2025, 1, 1), "total_steps": 10000},
            {"calendar_date": date(2025, 1, 2), "total_steps": 9000},
        ]
        result = make_page(rows, 100, 50, 0, DailySummary)
        assert len(result["data"]) == 2
        assert result["data"][0].total_steps == 10000
        assert result["pagination"]["total"] == 100
        assert result["pagination"]["limit"] == 50
        assert result["pagination"]["offset"] == 0
        assert result["pagination"]["has_more"] is True

    def test_make_page_has_more_false(self):
        """Test has_more is False when at end of results."""
        rows = [
            {"calendar_date": date(2025, 1, 1), "total_steps": 10000},
        ]
        result = make_page(rows, 1, 50, 0, DailySummary)
        assert result["pagination"]["has_more"] is False

    def test_make_page_has_more_true(self):
        """Test has_more is True when more results exist."""
        rows = [
            {"calendar_date": date(2025, 1, 1), "total_steps": 10000},
        ]
        result = make_page(rows, 100, 50, 0, DailySummary)
        assert result["pagination"]["has_more"] is True

    def test_make_page_with_offset(self):
        """Test make_page with offset."""
        rows = [
            {"calendar_date": date(2025, 1, 3), "total_steps": 8000},
        ]
        result = make_page(rows, 100, 50, 50, DailySummary)
        assert result["pagination"]["offset"] == 50
        assert result["pagination"]["has_more"] is True
