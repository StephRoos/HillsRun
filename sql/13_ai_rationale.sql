-- Adaptive coach (Chantier D, Lot D2): AI reasoning layer on daily readiness.
--
-- Adds the Claude-generated, NON-APPLIED natural-language explanation alongside
-- the rule-based D1 verdict. The agent explains and refines tone only; the
-- structured `verdict` column (written by D1) stays authoritative — a RED can
-- never be downgraded by the agent. Writing these columns never mutates a plan.
--
-- Applied manually to Neon + NAS after merge (see spec 03 §6). Do NOT auto-apply.
ALTER TABLE daily_recommendations
    ADD COLUMN IF NOT EXISTS ai_rationale TEXT;            -- short NL explanation

ALTER TABLE daily_recommendations
    ADD COLUMN IF NOT EXISTS ai_recommendation JSONB;      -- full structured rec

ALTER TABLE daily_recommendations
    ADD COLUMN IF NOT EXISTS ai_model VARCHAR(40);         -- Claude model id used

ALTER TABLE daily_recommendations
    ADD COLUMN IF NOT EXISTS ai_generated_at TIMESTAMPTZ;  -- when the agent ran
