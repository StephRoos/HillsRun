-- Table de tracking des migrations SQL
-- Permet de savoir quels fichiers ont déjà été appliqués et quand.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum TEXT
);

COMMENT ON TABLE schema_migrations IS 'Tracks applied SQL migration files';
