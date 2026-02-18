-- Multi-user migration: link Better-Auth users to garmin_user, add encrypted token storage
-- Run on NAS PostgreSQL (garmin_connect database)

-- 1. Add Better-Auth link and encrypted token columns to garmin_user
ALTER TABLE garmin_user
  ADD COLUMN IF NOT EXISTS better_auth_user_id TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS encrypted_tokens BYTEA,
  ADD COLUMN IF NOT EXISTS tokens_updated_at TIMESTAMPTZ;

-- 2. Add user_id to sync_state for per-user sync tracking
ALTER TABLE sync_state
  ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES garmin_user(user_id);

-- 3. Make sync_state unique per (user_id, category) instead of just category
-- Drop the old unique constraint on category alone
ALTER TABLE sync_state DROP CONSTRAINT IF EXISTS sync_state_category_key;
ALTER TABLE sync_state DROP CONSTRAINT IF EXISTS sync_state_pkey;

-- Add composite unique constraint
ALTER TABLE sync_state
  ADD CONSTRAINT sync_state_user_category_unique UNIQUE (user_id, category);

-- 4. Add index for efficient activity lookups by user
CREATE INDEX IF NOT EXISTS idx_activities_user_activity ON activities (user_id, activity_id);

-- 5. Backfill: set existing sync_state rows to the first user
UPDATE sync_state
  SET user_id = (SELECT user_id FROM garmin_user ORDER BY user_id LIMIT 1)
  WHERE user_id IS NULL;
