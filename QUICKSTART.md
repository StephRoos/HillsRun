# Quick Start Guide

Get your Garmin Connect sync running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Garmin Connect account

## Steps

### 1. Setup Environment

```bash
# Copy environment file
cp .env.example .env

# Edit and set your password
nano .env
# Set: POSTGRES_PASSWORD=your_secure_password
```

### 2. Configure Application

```bash
# Copy configuration
cp config/config.yaml.example config/config.yaml

# Configuration is ready to use with defaults
# Optionally edit to customize categories, sync mode, etc.
```

### 3. Authenticate with Garmin

```bash
# Install garminconnect
pip install garminconnect

# Authenticate (tokens will be saved)
python3 << 'EOF'
import garth
email = input("Garmin email: ")
password = input("Garmin password: ")
garth.login(email, password)
garth.save("~/.garminconnect")
print("✓ Authenticated!")
EOF
```

### 4. Initialize Database

```bash
# Option A: Using Make (recommended)
make setup

# Option B: Manual steps
docker-compose up -d postgres
sleep 10
./scripts/init_db.sh
```

### 5. First Sync

```bash
# Test with dry run
make sync-dry

# Run full sync (last 90 days)
make sync-full
```

### 6. Verify Data

```bash
# Check database
make status

# Or connect directly
make psql
# Then: SELECT * FROM sync_state;
```

### 7. Setup Automation (Optional)

```bash
# Make cron script executable
chmod +x cron/sync-cron.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /full/path/to/garmin-connect-sync/cron/sync-cron.sh
```

## Common Commands

```bash
make help              # Show all commands
make sync              # Incremental sync
make sync-full         # Full sync
make sync-dry          # Dry run
make backup            # Backup database
make status            # View sync status
make psql              # Database shell
```

## What's Next?

- See [docs/SETUP.md](docs/SETUP.md) for detailed setup
- Read [docs/SCHEMA.md](docs/SCHEMA.md) to understand the data
- Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) if you hit issues

## Data Categories Synced

✓ **Daily Health**: Steps, calories, heart rate, sleep, stress, body battery
✓ **Activities**: Running, cycling, swimming, and all sports
✓ **Body Composition**: Weight, BMI, body fat, muscle mass
✓ **Advanced Metrics**: HRV, SpO2, VO2 Max, respiration
✓ **Wellness**: Hydration tracking

## Sync Modes

- **Incremental** (default): Only sync new data since last sync
- **Full**: Sync all data for specified date range

## Support

Issues? Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) or open a GitHub issue.

Enjoy your Garmin data! 🏃‍♂️📊
