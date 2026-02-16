-- ============================================
-- Utility Functions for Data Operations
-- ============================================

-- Function to get the last sync date for a category
CREATE OR REPLACE FUNCTION get_last_sync_date(p_category VARCHAR)
RETURNS DATE AS $$
DECLARE
    last_date DATE;
BEGIN
    SELECT last_sync_date INTO last_date
    FROM sync_state
    WHERE category = p_category;

    RETURN last_date;
END;
$$ LANGUAGE plpgsql;

-- Function to upsert sync state
CREATE OR REPLACE FUNCTION upsert_sync_state(
    p_category VARCHAR,
    p_last_sync_date DATE,
    p_records_synced INTEGER,
    p_sync_status VARCHAR DEFAULT 'success',
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO sync_state (
        category,
        last_sync_date,
        last_sync_timestamp,
        records_synced,
        sync_status,
        error_message
    )
    VALUES (
        p_category,
        p_last_sync_date,
        CURRENT_TIMESTAMP,
        p_records_synced,
        p_sync_status,
        p_error_message
    )
    ON CONFLICT (category) DO UPDATE SET
        last_sync_date = EXCLUDED.last_sync_date,
        last_sync_timestamp = CURRENT_TIMESTAMP,
        records_synced = EXCLUDED.records_synced,
        sync_status = EXCLUDED.sync_status,
        error_message = EXCLUDED.error_message;
END;
$$ LANGUAGE plpgsql;

-- Function to get user_id or create if doesn't exist
CREATE OR REPLACE FUNCTION get_or_create_user(
    p_garmin_user_id VARCHAR,
    p_display_name VARCHAR DEFAULT NULL,
    p_email VARCHAR DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_user_id BIGINT;
BEGIN
    -- Try to get existing user
    SELECT user_id INTO v_user_id
    FROM garmin_user
    WHERE garmin_user_id = p_garmin_user_id;

    -- If not found, create new user
    IF v_user_id IS NULL THEN
        INSERT INTO garmin_user (garmin_user_id, display_name, email)
        VALUES (p_garmin_user_id, p_display_name, p_email)
        RETURNING user_id INTO v_user_id;
    END IF;

    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get activity count by date range
CREATE OR REPLACE FUNCTION get_activity_count_by_date_range(
    p_user_id BIGINT,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS INTEGER AS $$
DECLARE
    activity_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO activity_count
    FROM activities
    WHERE user_id = p_user_id
        AND start_timestamp::DATE BETWEEN p_start_date AND p_end_date;

    RETURN activity_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get daily health summary for date range
CREATE OR REPLACE FUNCTION get_daily_health_summary(
    p_user_id BIGINT,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    calendar_date DATE,
    steps INTEGER,
    distance_km NUMERIC,
    calories INTEGER,
    sleep_hours NUMERIC,
    avg_hr INTEGER,
    avg_stress INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.calendar_date,
        ds.total_steps,
        ROUND(ds.total_distance_meters / 1000.0, 2) AS distance_km,
        ds.total_calories,
        ROUND(sd.total_sleep_seconds / 3600.0, 1) AS sleep_hours,
        ds.average_heart_rate,
        ds.average_stress_level
    FROM daily_summary ds
    LEFT JOIN sleep_data sd ON ds.user_id = sd.user_id AND ds.calendar_date = sd.calendar_date
    WHERE ds.user_id = p_user_id
        AND ds.calendar_date BETWEEN p_start_date AND p_end_date
    ORDER BY ds.calendar_date DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old heart rate samples (optional - for data retention)
CREATE OR REPLACE FUNCTION cleanup_old_heart_rate_samples(
    p_days_to_keep INTEGER DEFAULT 365
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM heart_rate_samples
    WHERE timestamp < CURRENT_TIMESTAMP - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- View for recent activities summary
CREATE OR REPLACE VIEW recent_activities_summary AS
SELECT
    a.activity_id,
    a.user_id,
    a.activity_name,
    a.activity_type,
    a.sport_type,
    a.start_timestamp,
    ROUND(a.duration_seconds / 60.0, 1) AS duration_minutes,
    ROUND(a.distance_meters / 1000.0, 2) AS distance_km,
    a.calories,
    a.average_hr,
    a.max_hr,
    a.elevation_gain_meters,
    a.training_effect,
    a.pr,
    a.favorite
FROM activities a
ORDER BY a.start_timestamp DESC;

-- View for weekly health trends
CREATE OR REPLACE VIEW weekly_health_trends AS
SELECT
    user_id,
    DATE_TRUNC('week', calendar_date)::DATE AS week_start,
    AVG(total_steps) AS avg_steps,
    AVG(total_distance_meters / 1000.0) AS avg_distance_km,
    AVG(total_calories) AS avg_calories,
    AVG(resting_heart_rate) AS avg_resting_hr,
    AVG(average_stress_level) AS avg_stress,
    COUNT(*) AS days_recorded
FROM daily_summary
WHERE total_steps IS NOT NULL
GROUP BY user_id, DATE_TRUNC('week', calendar_date)
ORDER BY user_id, week_start DESC;
