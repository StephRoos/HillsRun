-- ============================================
-- Additional Indexes for Query Optimization
-- ============================================

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_daily_summary_user_date_steps ON daily_summary(user_id, calendar_date DESC, total_steps);
CREATE INDEX IF NOT EXISTS idx_activities_user_type_date ON activities(user_id, activity_type, start_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_body_comp_user_date_weight ON body_composition(user_id, timestamp DESC, weight_kg);

-- JSONB indexes for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_sleep_levels_gin ON sleep_data USING GIN (sleep_levels);
CREATE INDEX IF NOT EXISTS idx_stress_chart_gin ON stress_data USING GIN (stress_chart_values);
CREATE INDEX IF NOT EXISTS idx_body_battery_values_gin ON body_battery USING GIN (body_battery_values);
CREATE INDEX IF NOT EXISTS idx_activity_data_gin ON activities USING GIN (activity_data);

-- Partial indexes for frequently queried subsets
CREATE INDEX IF NOT EXISTS idx_activities_pr ON activities(user_id, start_timestamp DESC) WHERE pr = TRUE;
CREATE INDEX IF NOT EXISTS idx_activities_favorite ON activities(user_id, start_timestamp DESC) WHERE favorite = TRUE;
CREATE INDEX IF NOT EXISTS idx_activities_manual ON activities(user_id, start_timestamp DESC) WHERE manual_activity = TRUE;

-- Sync state index
CREATE INDEX IF NOT EXISTS idx_sync_state_category ON sync_state(category);
CREATE INDEX IF NOT EXISTS idx_sync_state_last_sync ON sync_state(last_sync_timestamp DESC);
