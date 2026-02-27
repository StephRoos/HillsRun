#!/usr/bin/env bash
# Setup logical replication from Neon Cloud to local PostgreSQL replica.
#
# Prerequisites:
#   1. Neon: wal_level=logical enabled (Project Settings > Logical Replication)
#   2. Neon: replicator role + publication created (see below)
#   3. Local: docker-compose.nas.yml running with postgres-replica healthy
#
# Neon setup (run once via psql on Neon):
#   CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '***';
#   GRANT SELECT ON ALL TABLES IN SCHEMA public TO replicator;
#   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO replicator;
#   CREATE PUBLICATION hillsrun_replica FOR ALL TABLES;
#
# Usage:
#   NEON_REPLICATION_CONNSTRING="postgresql://replicator:***@ep-***.neon.tech/neondb?sslmode=require" \
#   REPLICA_PASSWORD="***" \
#   ./scripts/setup-replica.sh

set -euo pipefail

REPLICA_HOST="${REPLICA_HOST:-localhost}"
REPLICA_PORT="${REPLICA_PORT:-5435}"
REPLICA_DB="${REPLICA_DB:-garmin_connect}"
REPLICA_USER="${REPLICA_USER:-garmin}"

if [ -z "${NEON_REPLICATION_CONNSTRING:-}" ]; then
  echo "ERROR: NEON_REPLICATION_CONNSTRING is required"
  echo "Example: postgresql://replicator:password@ep-xxx.neon.tech/neondb?sslmode=require"
  exit 1
fi

if [ -z "${REPLICA_PASSWORD:-}" ]; then
  echo "ERROR: REPLICA_PASSWORD is required"
  exit 1
fi

export PGPASSWORD="$REPLICA_PASSWORD"

echo "=== HillsRun Replica Setup ==="

# Step 1: Wait for PostgreSQL to be ready
echo "[1/3] Waiting for PostgreSQL replica to be ready..."
for i in $(seq 1 30); do
  if pg_isready -h "$REPLICA_HOST" -p "$REPLICA_PORT" -U "$REPLICA_USER" -d "$REPLICA_DB" > /dev/null 2>&1; then
    echo "  PostgreSQL is ready."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: PostgreSQL not ready after 30 attempts"
    exit 1
  fi
  sleep 2
done

# Step 2: Apply SQL migrations in order
echo "[2/3] Applying SQL migrations..."
SQL_DIR="$(cd "$(dirname "$0")/../sql" && pwd)"
for sql_file in "$SQL_DIR"/[0-9]*.sql; do
  filename=$(basename "$sql_file")
  echo "  Applying $filename..."
  psql -h "$REPLICA_HOST" -p "$REPLICA_PORT" -U "$REPLICA_USER" -d "$REPLICA_DB" \
    -f "$sql_file" -v ON_ERROR_STOP=0 2>&1 | grep -v "already exists" || true
done
echo "  Migrations complete."

# Step 3: Create subscription (copy_data=true for initial snapshot)
echo "[3/3] Creating replication subscription..."
psql -h "$REPLICA_HOST" -p "$REPLICA_PORT" -U "$REPLICA_USER" -d "$REPLICA_DB" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_subscription WHERE subname = 'hillsrun_sub') THEN
    EXECUTE format(
      'CREATE SUBSCRIPTION hillsrun_sub CONNECTION %L PUBLICATION hillsrun_replica WITH (copy_data = true)',
      '${NEON_REPLICATION_CONNSTRING}'
    );
    RAISE NOTICE 'Subscription created successfully.';
  ELSE
    RAISE NOTICE 'Subscription hillsrun_sub already exists, skipping.';
  END IF;
END
\$\$;
SQL

echo ""
echo "=== Setup complete ==="
echo "Verify with: ./scripts/check-replica.sh"
