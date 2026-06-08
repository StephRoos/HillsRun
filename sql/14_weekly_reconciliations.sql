-- Adaptive coach (Chantier D, Lot D4): weekly PROPOSE-ONLY plan adjustments.
--
-- Stores a proposal generated from the read-only adherence report (D3) plus the
-- recent daily readiness verdicts (D1). A proposal NEVER mutates the plan on its
-- own: training_plan_weeks / training_plan_sessions stay untouched until a user
-- explicitly applies it (status -> 'applied', applied_at set). Anti-thrashing is
-- enforced in code (at most one structural change per week).
--
-- Applied manually to Neon + NAS after merge (see spec 03 §6). Do NOT auto-apply.
CREATE TABLE IF NOT EXISTS weekly_reconciliations (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT REFERENCES training_plans(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    from_week INTEGER NOT NULL,            -- the evaluated / just-completed week
    target_week INTEGER NOT NULL,          -- the upcoming week the changes apply to
    compliance_pct NUMERIC(5, 1),          -- evaluated week compliance (context)
    proposal JSONB NOT NULL,               -- full WeeklyAdjustmentProposal payload
    status VARCHAR(16) NOT NULL DEFAULT 'proposed',  -- proposed | applied | dismissed
    applied BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMPTZ,
    UNIQUE(plan_id, from_week)             -- one live proposal per evaluated week
);

CREATE INDEX IF NOT EXISTS idx_weekly_reconciliations_plan
    ON weekly_reconciliations(plan_id, from_week DESC);
