#!/bin/bash
# Database Backup Script
# Creates a compressed backup of the PostgreSQL database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

# Database connection parameters
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-garmin_connect}"
DB_USER="${POSTGRES_USER:-garmin}"

# Backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/garmin_backup_$TIMESTAMP.sql.gz"

echo "========================================="
echo "Garmin Connect - Database Backup"
echo "========================================="
echo "Host: $DB_HOST"
echo "Database: $DB_NAME"
echo "Backup file: $BACKUP_FILE"
echo ""

# Create backup
echo "Creating backup..."
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --clean \
    --if-exists \
    --verbose \
    2>&1 | gzip > "$BACKUP_FILE"

# Check backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo "✓ Backup created successfully"
echo "  Size: $BACKUP_SIZE"
echo "  Location: $BACKUP_FILE"
echo ""

# Optional: Keep only last N backups (uncomment to enable)
# MAX_BACKUPS=7
# echo "Cleaning old backups (keeping last $MAX_BACKUPS)..."
# ls -t "$BACKUP_DIR"/garmin_backup_*.sql.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm
# echo "✓ Old backups cleaned"

echo "========================================="
echo "Backup complete!"
echo "========================================="
echo ""
echo "To restore this backup:"
echo "gunzip -c $BACKUP_FILE | PGPASSWORD=\$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
