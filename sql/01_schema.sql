-- ============================================
-- Garmin Connect to PostgreSQL - Database Schema
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Core Tables
-- ============================================

-- User profile
CREATE TABLE IF NOT EXISTS garmin_user (
    user_id BIGSERIAL PRIMARY KEY,
    garmin_user_id VARCHAR(100) UNIQUE,
    display_name VARCHAR(255),
    email VARCHAR(255),
    profile_image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Sync state tracking
CREATE TABLE IF NOT EXISTS sync_state (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) UNIQUE NOT NULL,
    last_sync_date DATE NOT NULL,
    last_sync_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    records_synced INTEGER DEFAULT 0,
    sync_status VARCHAR(20) DEFAULT 'success', -- success, partial, failed
    error_message TEXT,
    CONSTRAINT valid_category CHECK (category IN (
        'daily_health', 'activities', 'body_composition',
        'advanced_metrics', 'wellness'
    ))
);

-- ============================================
-- Daily Health Tables
-- ============================================

-- Daily summary data
CREATE TABLE IF NOT EXISTS daily_summary (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    total_steps INTEGER,
    step_goal INTEGER,
    total_distance_meters NUMERIC(10, 2),
    active_calories INTEGER,
    bmr_calories INTEGER, -- Basal Metabolic Rate
    total_calories INTEGER,
    floors_ascended NUMERIC(5, 1),
    floors_descended NUMERIC(5, 1),
    floors_goal INTEGER,
    moderate_intensity_minutes INTEGER,
    vigorous_intensity_minutes INTEGER,
    intensity_minutes_goal INTEGER,
    highly_active_seconds INTEGER,
    active_seconds INTEGER,
    sedentary_seconds INTEGER,
    sleeping_seconds INTEGER,
    max_heart_rate INTEGER,
    min_heart_rate INTEGER,
    resting_heart_rate INTEGER,
    average_heart_rate INTEGER,
    average_stress_level INTEGER,
    max_stress_level INTEGER,
    stress_qualifier VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- Heart rate samples (intraday)
CREATE TABLE IF NOT EXISTS heart_rate_samples (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    heart_rate INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, timestamp)
);

-- Sleep data
CREATE TABLE IF NOT EXISTS sleep_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    sleep_start_timestamp TIMESTAMPTZ,
    sleep_end_timestamp TIMESTAMPTZ,
    total_sleep_seconds INTEGER,
    deep_sleep_seconds INTEGER,
    light_sleep_seconds INTEGER,
    rem_sleep_seconds INTEGER,
    awake_seconds INTEGER,
    sleep_score INTEGER,
    sleep_quality VARCHAR(50),
    sleep_levels JSONB, -- Detailed sleep level data
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- Stress data
CREATE TABLE IF NOT EXISTS stress_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    average_stress_level INTEGER,
    max_stress_level INTEGER,
    rest_stress_duration_seconds INTEGER,
    activity_stress_duration_seconds INTEGER,
    uncategorized_stress_duration_seconds INTEGER,
    low_stress_duration_seconds INTEGER,
    medium_stress_duration_seconds INTEGER,
    high_stress_duration_seconds INTEGER,
    stress_chart_values JSONB, -- Intraday stress samples
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- Body Battery (energy levels)
CREATE TABLE IF NOT EXISTS body_battery (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    charged_value INTEGER, -- Battery level gained
    drained_value INTEGER, -- Battery level lost
    highest_value INTEGER,
    lowest_value INTEGER,
    start_timestamp TIMESTAMPTZ,
    end_timestamp TIMESTAMPTZ,
    body_battery_values JSONB, -- Intraday body battery samples
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- ============================================
-- Body Composition Tables
-- ============================================

CREATE TABLE IF NOT EXISTS body_composition (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    weight_kg NUMERIC(6, 2),
    bmi NUMERIC(5, 2),
    body_fat_percentage NUMERIC(5, 2),
    body_water_percentage NUMERIC(5, 2),
    bone_mass_kg NUMERIC(5, 2),
    muscle_mass_kg NUMERIC(6, 2),
    metabolic_age INTEGER,
    visceral_fat_rating INTEGER,
    basal_met NUMERIC(7, 2), -- Basal metabolic rate
    active_met NUMERIC(7, 2), -- Active metabolic rate
    physique_rating INTEGER,
    source_type VARCHAR(50), -- manual, scale, estimate
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, timestamp)
);

-- ============================================
-- Advanced Metrics Tables
-- ============================================

-- Heart Rate Variability
CREATE TABLE IF NOT EXISTS hrv_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    weekly_avg NUMERIC(6, 2),
    last_night_avg NUMERIC(6, 2),
    last_night_5_min_high NUMERIC(6, 2),
    hrv_status VARCHAR(50), -- balanced, unbalanced, low, high
    feedback_phrase TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- SpO2 (Blood Oxygen Saturation)
CREATE TABLE IF NOT EXISTS spo2_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    average_spo2_percentage NUMERIC(5, 2),
    lowest_spo2_percentage NUMERIC(5, 2),
    latest_spo2_reading NUMERIC(5, 2),
    latest_spo2_reading_timestamp TIMESTAMPTZ,
    spo2_values JSONB, -- Intraday SpO2 samples
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- Training Readiness / Recovery
CREATE TABLE IF NOT EXISTS training_readiness (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    score INTEGER,
    score_feedback VARCHAR(50), -- poor, fair, good, excellent
    hrv_status VARCHAR(50),
    sleep_score INTEGER,
    recent_training_load INTEGER,
    acute_load NUMERIC(8, 2),
    chronic_load NUMERIC(8, 2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- Fitness metrics (VO2 Max, Fitness Age, etc.)
CREATE TABLE IF NOT EXISTS fitness_metrics (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    vo2_max NUMERIC(5, 2),
    vo2_max_running NUMERIC(5, 2),
    vo2_max_cycling NUMERIC(5, 2),
    fitness_age INTEGER,
    lactate_threshold_bpm INTEGER,
    lactate_threshold_speed NUMERIC(5, 2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- Respiration data
CREATE TABLE IF NOT EXISTS respiration_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    avg_waking_respiration_rate NUMERIC(5, 2),
    max_waking_respiration_rate NUMERIC(5, 2),
    min_waking_respiration_rate NUMERIC(5, 2),
    avg_sleep_respiration_rate NUMERIC(5, 2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- ============================================
-- Activities Tables
-- ============================================

CREATE TABLE IF NOT EXISTS activities (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    activity_id BIGINT UNIQUE NOT NULL,
    activity_name VARCHAR(255),
    activity_type VARCHAR(100),
    sport_type VARCHAR(100),
    start_timestamp TIMESTAMPTZ,
    duration_seconds INTEGER,
    distance_meters NUMERIC(10, 2),
    average_speed NUMERIC(8, 4),
    max_speed NUMERIC(8, 4),
    average_pace NUMERIC(8, 4),
    max_pace NUMERIC(8, 4),
    calories INTEGER,
    average_hr INTEGER,
    max_hr INTEGER,
    average_running_cadence NUMERIC(6, 2),
    max_running_cadence INTEGER,
    average_bike_cadence NUMERIC(6, 2),
    max_bike_cadence INTEGER,
    average_power NUMERIC(8, 2),
    max_power INTEGER,
    normalized_power NUMERIC(8, 2),
    training_stress_score NUMERIC(6, 2),
    intensity_factor NUMERIC(4, 3),
    elevation_gain_meters NUMERIC(8, 2),
    elevation_loss_meters NUMERIC(8, 2),
    min_elevation_meters NUMERIC(8, 2),
    max_elevation_meters NUMERIC(8, 2),
    average_temperature NUMERIC(5, 2),
    max_temperature NUMERIC(5, 2),
    min_temperature NUMERIC(5, 2),
    training_effect NUMERIC(3, 1),
    aerobic_training_effect NUMERIC(3, 1),
    anaerobic_training_effect NUMERIC(3, 1),
    avg_vertical_oscillation NUMERIC(6, 2),
    avg_ground_contact_time INTEGER,
    avg_stride_length NUMERIC(6, 2),
    vo2_max_value NUMERIC(5, 2),
    lactate_threshold_bpm INTEGER,
    device_name VARCHAR(100),
    description TEXT,
    manual_activity BOOLEAN DEFAULT FALSE,
    pr BOOLEAN DEFAULT FALSE, -- Personal Record
    favorite BOOLEAN DEFAULT FALSE,
    auto_calc_calories BOOLEAN,
    num_laps INTEGER,
    activity_data JSONB, -- Full activity JSON for reference
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Activity splits/laps
CREATE TABLE IF NOT EXISTS activity_splits (
    id BIGSERIAL PRIMARY KEY,
    activity_id BIGINT REFERENCES activities(activity_id) ON DELETE CASCADE,
    split_index INTEGER NOT NULL,
    split_type VARCHAR(50), -- lap, auto, manual
    distance_meters NUMERIC(10, 2),
    duration_seconds INTEGER,
    average_speed NUMERIC(8, 4),
    average_hr INTEGER,
    max_hr INTEGER,
    average_power NUMERIC(8, 2),
    max_power INTEGER,
    average_cadence NUMERIC(6, 2),
    elevation_gain_meters NUMERIC(8, 2),
    elevation_loss_meters NUMERIC(8, 2),
    start_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(activity_id, split_index)
);

-- ============================================
-- Wellness Tables
-- ============================================

-- Hydration tracking
CREATE TABLE IF NOT EXISTS hydration_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    calendar_date DATE NOT NULL,
    total_hydration_ml INTEGER,
    hydration_goal_ml INTEGER,
    hydration_entries JSONB, -- Individual hydration log entries
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, calendar_date)
);

-- ============================================
-- Indexes for Performance
-- ============================================

-- User indexes
CREATE INDEX IF NOT EXISTS idx_garmin_user_garmin_user_id ON garmin_user(garmin_user_id);

-- Daily summary indexes
CREATE INDEX IF NOT EXISTS idx_daily_summary_user_date ON daily_summary(user_id, calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_summary_date ON daily_summary(calendar_date DESC);

-- Heart rate indexes
CREATE INDEX IF NOT EXISTS idx_heart_rate_user_timestamp ON heart_rate_samples(user_id, timestamp DESC);

-- Sleep data indexes
CREATE INDEX IF NOT EXISTS idx_sleep_user_date ON sleep_data(user_id, calendar_date DESC);

-- Stress data indexes
CREATE INDEX IF NOT EXISTS idx_stress_user_date ON stress_data(user_id, calendar_date DESC);

-- Body battery indexes
CREATE INDEX IF NOT EXISTS idx_body_battery_user_date ON body_battery(user_id, calendar_date DESC);

-- Body composition indexes
CREATE INDEX IF NOT EXISTS idx_body_comp_user_timestamp ON body_composition(user_id, timestamp DESC);

-- Advanced metrics indexes
CREATE INDEX IF NOT EXISTS idx_hrv_user_date ON hrv_data(user_id, calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_spo2_user_date ON spo2_data(user_id, calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_training_readiness_user_date ON training_readiness(user_id, calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_fitness_metrics_user_date ON fitness_metrics(user_id, calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_respiration_user_date ON respiration_data(user_id, calendar_date DESC);

-- Activities indexes
CREATE INDEX IF NOT EXISTS idx_activities_user_start ON activities(user_id, start_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activities_start ON activities(start_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_sport_type ON activities(sport_type);

-- Activity splits indexes
CREATE INDEX IF NOT EXISTS idx_activity_splits_activity ON activity_splits(activity_id);

-- Hydration indexes
CREATE INDEX IF NOT EXISTS idx_hydration_user_date ON hydration_data(user_id, calendar_date DESC);

-- ============================================
-- Update Timestamp Trigger Function
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to all tables with updated_at
CREATE TRIGGER update_garmin_user_updated_at BEFORE UPDATE ON garmin_user
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_summary_updated_at BEFORE UPDATE ON daily_summary
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sleep_data_updated_at BEFORE UPDATE ON sleep_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stress_data_updated_at BEFORE UPDATE ON stress_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_body_battery_updated_at BEFORE UPDATE ON body_battery
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_body_composition_updated_at BEFORE UPDATE ON body_composition
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_hrv_data_updated_at BEFORE UPDATE ON hrv_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_spo2_data_updated_at BEFORE UPDATE ON spo2_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_readiness_updated_at BEFORE UPDATE ON training_readiness
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fitness_metrics_updated_at BEFORE UPDATE ON fitness_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_respiration_data_updated_at BEFORE UPDATE ON respiration_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_activities_updated_at BEFORE UPDATE ON activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_hydration_data_updated_at BEFORE UPDATE ON hydration_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
