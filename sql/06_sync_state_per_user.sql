-- Migration: sync_state per-user support
-- Already applied to production DB — this file documents the changes.
--
-- Context: The original sync_state table had a UNIQUE constraint on `category` alone,
-- which prevented per-user sync tracking and caused the scheduler's ON CONFLICT
-- to fail with "there is no unique or exclusion constraint matching the ON CONFLICT".

-- 1. Drop the old single-user unique constraint on category
ALTER TABLE sync_state DROP CONSTRAINT IF EXISTS sync_state_category_key;

-- 2. Add user_id column (nullable for backward compat with global sync entries)
ALTER TABLE sync_state ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES garmin_user(user_id) ON DELETE CASCADE;

-- 3. Create composite unique index for per-user sync state
CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_user_category ON sync_state (user_id, category);

-- 4. Drop the old CHECK constraint on category to allow new categories
ALTER TABLE sync_state DROP CONSTRAINT IF EXISTS valid_category;

-- ============================================
-- Other schema changes applied to production
-- ============================================

-- garmin_user: Better-Auth link + encrypted tokens
ALTER TABLE garmin_user ADD COLUMN IF NOT EXISTS better_auth_user_id VARCHAR(36) UNIQUE;
ALTER TABLE garmin_user ADD COLUMN IF NOT EXISTS encrypted_tokens BYTEA;
ALTER TABLE garmin_user ADD COLUMN IF NOT EXISTS tokens_updated_at TIMESTAMPTZ;

-- activities: composite unique on (user_id, activity_id) instead of just activity_id
-- Note: This requires dropping the old unique constraint first
-- ALTER TABLE activities DROP CONSTRAINT IF EXISTS activities_activity_id_key;
-- CREATE UNIQUE INDEX IF NOT EXISTS uq_activities_user_activity ON activities (user_id, activity_id);

-- activities: custom_name column for user-given names
ALTER TABLE activities ADD COLUMN IF NOT EXISTS custom_name VARCHAR(255);
