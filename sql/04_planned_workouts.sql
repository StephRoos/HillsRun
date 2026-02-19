-- Planned workouts table for training calendar
CREATE TABLE IF NOT EXISTS planned_workouts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    planned_date DATE NOT NULL,
    sport_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    planned_duration_seconds INTEGER,
    planned_distance_meters NUMERIC(10, 2),
    intensity VARCHAR(20) NOT NULL DEFAULT 'moderate',
    completed BOOLEAN DEFAULT FALSE,
    created_by_user_id VARCHAR(36),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_planned_workouts_user_date ON planned_workouts(user_id, planned_date DESC);

CREATE TRIGGER update_planned_workouts_updated_at BEFORE UPDATE ON planned_workouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
