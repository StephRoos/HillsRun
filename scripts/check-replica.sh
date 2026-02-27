#!/usr/bin/env bash
# Monitor Neon → NAS logical replication health.
#
# Checks:
#   1. Subscription status (active/inactive)
#   2. Replication lag
#   3. Data freshness (latest activity timestamp)
#
# Usage:
#   REPLICA_PASSWORD="***" ./scripts/check-replica.sh

set -euo pipefail

REPLICA_HOST="${REPLICA_HOST:-localhost}"
REPLICA_PORT="${REPLICA_PORT:-5435}"
REPLICA_DB="${REPLICA_DB:-garmin_connect}"
REPLICA_USER="${REPLICA_USER:-garmin}"
MAX_LAG_SECONDS="${MAX_LAG_SECONDS:-300}"

if [ -z "${REPLICA_PASSWORD:-}" ]; then
  echo "ERROR: REPLICA_PASSWORD is required"
  exit 1
fi

export PGPASSWORD="$REPLICA_PASSWORD"

PSQL="psql -h $REPLICA_HOST -p $REPLICA_PORT -U $REPLICA_USER -d $REPLICA_DB -t -A"

echo "=== HillsRun Replica Health Check ==="
echo "Time: $(date -Iseconds)"
echo ""

# Check 1: Subscription status
echo "--- Subscription Status ---"
sub_status=$($PSQL -c "
  SELECT subname || '|' || subenabled
  FROM pg_subscription
  WHERE subname = 'hillsrun_sub';
" 2>/dev/null || echo "")

if [ -z "$sub_status" ]; then
  echo "CRITICAL: Subscription 'hillsrun_sub' not found!"
  exit 2
fi

sub_enabled=$(echo "$sub_status" | cut -d'|' -f2)
if [ "$sub_enabled" = "t" ]; then
  echo "Subscription: ACTIVE"
else
  echo "CRITICAL: Subscription is DISABLED!"
  exit 2
fi

# Check 2: Replication worker status
echo ""
echo "--- Replication Workers ---"
worker_info=$($PSQL -c "
  SELECT pid || '|' || COALESCE(received_lsn::text, 'none') || '|' || COALESCE(latest_end_lsn::text, 'none')
  FROM pg_stat_subscription
  WHERE subname = 'hillsrun_sub' AND pid IS NOT NULL;
" 2>/dev/null || echo "")

if [ -z "$worker_info" ]; then
  echo "WARNING: No active replication worker"
else
  echo "Worker PID: $(echo "$worker_info" | cut -d'|' -f1)"
  echo "Received LSN: $(echo "$worker_info" | cut -d'|' -f2)"
  echo "Latest end LSN: $(echo "$worker_info" | cut -d'|' -f3)"
fi

# Check 3: Replication lag
echo ""
echo "--- Replication Lag ---"
lag_info=$($PSQL -c "
  SELECT COALESCE(
    EXTRACT(EPOCH FROM (now() - latest_end_time))::int,
    -1
  )
  FROM pg_stat_subscription
  WHERE subname = 'hillsrun_sub';
" 2>/dev/null || echo "-1")

lag_seconds=$(echo "$lag_info" | tr -d ' ')
if [ "$lag_seconds" = "-1" ] || [ -z "$lag_seconds" ]; then
  echo "WARNING: Cannot determine replication lag"
elif [ "$lag_seconds" -gt "$MAX_LAG_SECONDS" ]; then
  echo "CRITICAL: Replication lag is ${lag_seconds}s (threshold: ${MAX_LAG_SECONDS}s)"
  exit 2
else
  echo "Lag: ${lag_seconds}s (threshold: ${MAX_LAG_SECONDS}s) - OK"
fi

# Check 4: Data freshness
echo ""
echo "--- Data Freshness ---"
latest_activity=$($PSQL -c "
  SELECT COALESCE(MAX(start_time)::text, 'no data')
  FROM activities;
" 2>/dev/null || echo "unknown")
echo "Latest activity: $latest_activity"

row_counts=$($PSQL -c "
  SELECT 'activities: ' || count(*) FROM activities
  UNION ALL
  SELECT 'daily_summary: ' || count(*) FROM daily_summary
  UNION ALL
  SELECT 'sleep_data: ' || count(*) FROM sleep_data;
" 2>/dev/null || echo "unknown")
echo "Row counts:"
echo "$row_counts" | while read -r line; do
  echo "  $line"
done

echo ""
echo "=== Check complete ==="
