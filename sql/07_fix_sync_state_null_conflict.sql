-- Migration: Fix ON CONFLICT for sync_state with NULL user_id
--
-- Context: PostgreSQL treats NULL != NULL in unique indexes, so
-- ON CONFLICT (user_id, category) never triggers for NULL user_id rows.
-- This adds a partial unique index for the legacy global sync entries.

-- Partial index for NULL user_id entries (legacy global sync)
CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_null_user_category
    ON sync_state (category) WHERE user_id IS NULL;

-- Update the upsert_sync_state function to handle per-user sync
CREATE OR REPLACE FUNCTION upsert_sync_state(
    p_user_id BIGINT,
    p_category VARCHAR,
    p_last_sync_date DATE,
    p_records_synced INTEGER,
    p_sync_status VARCHAR DEFAULT 'success',
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    IF p_user_id IS NOT NULL THEN
        INSERT INTO sync_state (user_id, category, last_sync_date, last_sync_timestamp, records_synced, sync_status, error_message)
        VALUES (p_user_id, p_category, p_last_sync_date, CURRENT_TIMESTAMP, p_records_synced, p_sync_status, p_error_message)
        ON CONFLICT (user_id, category) DO UPDATE SET
            last_sync_date = EXCLUDED.last_sync_date,
            last_sync_timestamp = CURRENT_TIMESTAMP,
            records_synced = EXCLUDED.records_synced,
            sync_status = EXCLUDED.sync_status,
            error_message = EXCLUDED.error_message;
    ELSE
        INSERT INTO sync_state (category, last_sync_date, last_sync_timestamp, records_synced, sync_status, error_message)
        VALUES (p_category, p_last_sync_date, CURRENT_TIMESTAMP, p_records_synced, p_sync_status, p_error_message)
        ON CONFLICT (category) WHERE user_id IS NULL DO UPDATE SET
            last_sync_date = EXCLUDED.last_sync_date,
            last_sync_timestamp = CURRENT_TIMESTAMP,
            records_synced = EXCLUDED.records_synced,
            sync_status = EXCLUDED.sync_status,
            error_message = EXCLUDED.error_message;
    END IF;
END;
$$ LANGUAGE plpgsql;
