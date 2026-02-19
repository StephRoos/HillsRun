-- Coach Role: coach_athletes link table, invite_codes, coaching_enabled flag

-- coach_athletes: links coach (Better-Auth ID) → athlete (garmin_user.user_id)
CREATE TABLE IF NOT EXISTS coach_athletes (
    id                   BIGSERIAL PRIMARY KEY,
    coach_better_auth_id VARCHAR(36) NOT NULL,
    athlete_user_id      BIGINT NOT NULL REFERENCES garmin_user(user_id) ON DELETE CASCADE,
    status               VARCHAR(20) NOT NULL DEFAULT 'active',
    linked_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    removed_at           TIMESTAMPTZ,
    UNIQUE(coach_better_auth_id, athlete_user_id)
);

-- invite_codes: single-use, 72h expiry
CREATE TABLE IF NOT EXISTS invite_codes (
    id                   BIGSERIAL PRIMARY KEY,
    code                 VARCHAR(12) NOT NULL UNIQUE,
    coach_better_auth_id VARCHAR(36) NOT NULL,
    status               VARCHAR(20) NOT NULL DEFAULT 'pending',
    redeemed_by_user_id  BIGINT REFERENCES garmin_user(user_id) ON DELETE SET NULL,
    created_at           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at           TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '72 hours'),
    redeemed_at          TIMESTAMPTZ
);

-- coaching_enabled flag on garmin_user
ALTER TABLE garmin_user ADD COLUMN IF NOT EXISTS coaching_enabled BOOLEAN NOT NULL DEFAULT FALSE;
