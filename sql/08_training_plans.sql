-- Training plans: athlete profiles, race targets, plans, weeks, sessions
-- Applied: pending

-- Extended athlete profile (distinct from garmin_user)
CREATE TABLE IF NOT EXISTS athlete_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    birth_date DATE,
    gender VARCHAR(10),
    height_cm NUMERIC(5,1),
    experience_level VARCHAR(20) NOT NULL DEFAULT 'intermediate',
    available_days_per_week INTEGER DEFAULT 4 CHECK (available_days_per_week BETWEEN 2 AND 7),
    available_slots JSONB,
    injury_history TEXT,
    has_hill_access BOOLEAN DEFAULT TRUE,
    has_gym_access BOOLEAN DEFAULT FALSE,
    fc_max INTEGER,
    fc_repos INTEGER,
    fthr INTEGER,
    strava_access_token TEXT,
    strava_refresh_token TEXT,
    strava_token_expires_at TIMESTAMPTZ,
    strava_athlete_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Race target
CREATE TABLE IF NOT EXISTS race_targets (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    race_name VARCHAR(255) NOT NULL,
    race_date DATE NOT NULL,
    distance_km NUMERIC(7,2) NOT NULL,
    elevation_gain_m INTEGER DEFAULT 0,
    elevation_loss_m INTEGER DEFAULT 0,
    altitude_min_m INTEGER DEFAULT 0,
    altitude_max_m INTEGER DEFAULT 0,
    technical_percent INTEGER DEFAULT 0 CHECK (technical_percent BETWEEN 0 AND 100),
    cutoff_hours NUMERIC(5,2),
    itra_points INTEGER,
    objective VARCHAR(20) NOT NULL DEFAULT 'finish',
    elevation_profile JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Training plan (master entity)
CREATE TABLE IF NOT EXISTS training_plans (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    race_target_id BIGINT NOT NULL REFERENCES race_targets(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_weeks INTEGER NOT NULL,
    experience_level VARCHAR(20) NOT NULL,
    generation_params JSONB,
    created_by_user_id VARCHAR(36),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Plan weeks (phases + targets)
CREATE TABLE IF NOT EXISTS training_plan_weeks (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES training_plans(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL,
    phase VARCHAR(20) NOT NULL,
    is_recovery_week BOOLEAN DEFAULT FALSE,
    target_tss NUMERIC(8,2),
    target_volume_km NUMERIC(7,2),
    target_elevation_m INTEGER,
    target_sessions INTEGER,
    notes TEXT,
    UNIQUE(plan_id, week_number)
);

-- Plan sessions (linked to planned_workouts)
CREATE TABLE IF NOT EXISTS training_plan_sessions (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES training_plans(id) ON DELETE CASCADE,
    week_id BIGINT NOT NULL REFERENCES training_plan_weeks(id) ON DELETE CASCADE,
    planned_workout_id BIGINT REFERENCES planned_workouts(id) ON DELETE SET NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    session_type VARCHAR(10) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    sport_type VARCHAR(100) NOT NULL DEFAULT 'trail_running',
    target_duration_seconds INTEGER,
    target_distance_meters NUMERIC(10,2),
    target_elevation_gain_m INTEGER,
    target_tss NUMERIC(6,2),
    hr_zone_primary INTEGER,
    intensity VARCHAR(20) NOT NULL DEFAULT 'moderate',
    blocks JSONB,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Extend planned_workouts with training plan columns
ALTER TABLE planned_workouts ADD COLUMN IF NOT EXISTS plan_id BIGINT REFERENCES training_plans(id) ON DELETE SET NULL;
ALTER TABLE planned_workouts ADD COLUMN IF NOT EXISTS session_type VARCHAR(10);
ALTER TABLE planned_workouts ADD COLUMN IF NOT EXISTS hr_zone_primary INTEGER;
ALTER TABLE planned_workouts ADD COLUMN IF NOT EXISTS target_elevation_gain_m INTEGER;
ALTER TABLE planned_workouts ADD COLUMN IF NOT EXISTS blocks JSONB;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_athlete_profiles_user ON athlete_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_race_targets_user ON race_targets(user_id);
CREATE INDEX IF NOT EXISTS idx_training_plans_user ON training_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_training_plans_status ON training_plans(user_id, status);
CREATE INDEX IF NOT EXISTS idx_plan_weeks_plan ON training_plan_weeks(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_sessions_plan ON training_plan_sessions(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_sessions_week ON training_plan_sessions(week_id);
CREATE INDEX IF NOT EXISTS idx_planned_workouts_plan ON planned_workouts(plan_id) WHERE plan_id IS NOT NULL;

-- Triggers for updated_at
CREATE TRIGGER update_athlete_profiles_updated_at BEFORE UPDATE ON athlete_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_race_targets_updated_at BEFORE UPDATE ON race_targets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_plans_updated_at BEFORE UPDATE ON training_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plan_sessions_updated_at BEFORE UPDATE ON training_plan_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
