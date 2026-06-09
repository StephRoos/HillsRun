-- Adaptive coach (Chantier D, Lot D1): daily HRV-baseline recommendations.
--
-- Stores the rule-based daily readiness verdict (GREEN/AMBER/RED/
-- insufficient_baseline) plus its suggested, NON-APPLIED session modification.
-- Writing a row here never mutates planned_workouts or training_plan_sessions.
--
-- Applied manually to Neon + NAS after merge (see spec 03 §6). Do NOT auto-apply.
CREATE TABLE IF NOT EXISTS daily_recommendations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    verdict VARCHAR(24) NOT NULL,          -- green | amber | red | insufficient_baseline
    reason TEXT,
    suggested_modification JSONB,          -- non-applied session change proposal
    hrv_value NUMERIC(6, 2),               -- today's overnight rMSSD avg (ms)
    baseline_low NUMERIC(6, 2),            -- lower band bound (ms)
    baseline_high NUMERIC(6, 2),           -- upper band bound (ms)
    accepted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_recommendations_user_date
    ON daily_recommendations(user_id, date DESC);
