#!/bin/bash
# Garmin Connect Daily Sync Script
# This script is designed to be run via cron

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Log directory
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Log file with rotation
LOG_FILE="$LOG_DIR/cron-sync.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Function to log messages
log() {
    echo "[$DATE] $1" >> "$LOG_FILE"
}

log "========================================="
log "Starting Garmin Connect sync"
log "========================================="

# Change to project directory
cd "$PROJECT_DIR"

# Load environment variables if .env exists
if [ -f "$PROJECT_DIR/.env" ]; then
    log "Loading environment from .env"
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Run sync using docker-compose
log "Running docker-compose sync..."
if docker-compose --profile sync run --rm garmin-sync >> "$LOG_FILE" 2>&1; then
    log "Sync completed successfully"
    EXIT_CODE=0
else
    EXIT_CODE=$?
    log "Sync failed with exit code: $EXIT_CODE"
fi

log "========================================="
log "Sync finished"
log "========================================="
echo "" >> "$LOG_FILE"

# Rotate log if it's too large (keep last 10MB)
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$LOG_SIZE" -gt 10485760 ]; then
        log "Rotating log file (size: $LOG_SIZE bytes)"
        mv "$LOG_FILE" "$LOG_FILE.old"
        tail -c 5242880 "$LOG_FILE.old" > "$LOG_FILE"
        rm "$LOG_FILE.old"
    fi
fi

exit $EXIT_CODE
