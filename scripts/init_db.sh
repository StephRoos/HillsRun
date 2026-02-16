#!/bin/bash
# Database Initialization Script
# Initializes the PostgreSQL database with schema

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SQL_DIR="$PROJECT_DIR/sql"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

# Database connection parameters
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-garmin_connect}"
DB_USER="${POSTGRES_USER:-garmin}"

echo "========================================="
echo "Garmin Connect - Database Initialization"
echo "========================================="
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Check if PostgreSQL is accessible
echo "Checking database connection..."
if ! PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo "Error: Cannot connect to database"
    echo "Please ensure:"
    echo "1. PostgreSQL is running"
    echo "2. Database '$DB_NAME' exists"
    echo "3. User '$DB_USER' has access"
    echo "4. POSTGRES_PASSWORD is set correctly"
    exit 1
fi

echo "✓ Database connection successful"
echo ""

# Apply SQL files in order
for SQL_FILE in "$SQL_DIR"/*.sql; do
    if [ -f "$SQL_FILE" ]; then
        FILENAME=$(basename "$SQL_FILE")
        echo "Applying $FILENAME..."
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_FILE"
        echo "✓ $FILENAME applied successfully"
        echo ""
    fi
done

echo "========================================="
echo "Database initialization complete!"
echo "========================================="
