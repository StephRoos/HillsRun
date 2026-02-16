# Detailed Setup Guide

This guide provides comprehensive setup instructions for the Garmin Connect to PostgreSQL sync application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Garmin Authentication](#garmin-authentication)
4. [Database Setup](#database-setup)
5. [Application Configuration](#application-configuration)
6. [First Sync](#first-sync)
7. [Automation Setup](#automation-setup)
8. [NAS Deployment](#nas-deployment)

## Prerequisites

### Required

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Garmin Connect Account** with activity data
- **Minimum Storage**: 1GB for database + logs
- **Network**: Internet access for Garmin Connect API

### Optional

- Python 3.11+ (for local development)
- PostgreSQL client tools (psql, pg_dump)

## Initial Setup

### 1. Clone Repository

```bash
cd /path/to/your/projects
git clone <repository-url> garmin-connect-sync
cd garmin-connect-sync
```

### 2. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```bash
# Required
POSTGRES_PASSWORD=your_secure_password_here

# Optional - adjust as needed
POSTGRES_DB=garmin_connect
POSTGRES_USER=garmin
POSTGRES_PORT=5432
GARMIN_TOKENS_DIR=~/.garminconnect
LOG_LEVEL=INFO
```

**Security Note**: Use a strong password with at least 16 characters including letters, numbers, and symbols.

### 3. Create Configuration

```bash
cp config/config.yaml.example config/config.yaml
```

Edit `config/config.yaml` to customize:
- Categories to sync
- Sync mode (incremental/full)
- Rate limiting
- Logging preferences

See [config/README.md](../config/README.md) for all options.

## Garmin Authentication

Garmin Connect uses OAuth tokens that remain valid for approximately 1 year.

### Method 1: Using Python (Recommended)

```bash
# Install garminconnect if not already installed
pip install garminconnect

# Authenticate and save tokens
python3 << 'EOF'
import garth
from getpass import getpass

email = input("Garmin email: ")
password = getpass("Garmin password: ")

garth.login(email, password)
garth.save("~/.garminconnect")
print("✓ Authentication successful! Tokens saved to ~/.garminconnect")
EOF
```

### Method 2: Using garminconnect CLI

```bash
pip install garminconnect

# This will prompt for email/password and save tokens
garmin-login
```

### Verify Authentication

```bash
ls -la ~/.garminconnect/
# Should see: oauth1_token.json and oauth2_token.json
```

### Multi-Factor Authentication (MFA)

If your Garmin account uses MFA:

1. You'll be prompted for the MFA code during authentication
2. Enter the code from your authenticator app
3. Tokens will be saved after successful MFA verification

## Database Setup

### 1. Start PostgreSQL

```bash
docker-compose up -d postgres
```

This creates a PostgreSQL 15 container with persistent storage.

### 2. Wait for Database to Initialize

```bash
# Wait about 10 seconds for PostgreSQL to start
sleep 10

# Or check status
docker-compose ps
# Should show postgres as "healthy"
```

### 3. Initialize Schema

```bash
./scripts/init_db.sh
```

This script:
- Creates all tables
- Adds indexes
- Creates utility functions and views

### 4. Verify Database

```bash
# Connect to database
docker-compose exec postgres psql -U garmin -d garmin_connect

# List tables
\dt

# Should see: garmin_user, sync_state, daily_summary, activities, etc.

# Exit
\q
```

## Application Configuration

### Database Connection

In `config/config.yaml`:

```yaml
database:
  host: postgres  # Docker service name
  port: 5432
  database: garmin_connect
  user: garmin
  password: ${POSTGRES_PASSWORD}  # From .env file
```

### Garmin Tokens

Ensure tokens directory is correctly configured:

```yaml
garmin:
  tokens_dir: ~/.garminconnect  # For local development
  # or for Docker:
  tokens_dir: /tokens  # If mounting from different location
```

### Sync Settings

Configure what and how to sync:

```yaml
sync:
  categories:
    - daily_health      # Essential daily metrics
    - activities        # Sports activities
    - body_composition  # Weight, body fat, etc.
    - advanced_metrics  # HRV, SpO2, VO2 Max
    - wellness          # Hydration

  mode: incremental  # or 'full' for complete resync
  days_back: 90      # For full sync
  rate_limit_delay: 0.5  # Seconds between API calls
```

## First Sync

### Test Dry Run

Before syncing real data, test the configuration:

```bash
docker-compose --profile sync run --rm garmin-sync --dry-run
```

This shows what would be synced without actually syncing.

### Initial Full Sync

Sync historical data (default: last 90 days):

```bash
docker-compose --profile sync run --rm garmin-sync --full
```

**Note**: Full sync can take 15-30 minutes depending on data volume.

### Monitor Progress

In another terminal, watch logs:

```bash
# Watch application logs
docker-compose --profile sync logs -f garmin-sync

# Or check log files
tail -f logs/garmin_sync_*.log
```

### Verify Sync Results

After sync completes, check the database:

```sql
-- Connect to database
docker-compose exec postgres psql -U garmin -d garmin_connect

-- Check sync status
SELECT * FROM sync_state;

-- Count records
SELECT
    (SELECT COUNT(*) FROM daily_summary) as daily_summaries,
    (SELECT COUNT(*) FROM activities) as activities,
    (SELECT COUNT(*) FROM body_composition) as body_comp,
    (SELECT COUNT(*) FROM sleep_data) as sleep_records;
```

## Automation Setup

### Cron Setup (Linux/macOS)

1. **Make script executable**:
   ```bash
   chmod +x cron/sync-cron.sh
   ```

2. **Test script manually**:
   ```bash
   ./cron/sync-cron.sh
   ```

3. **Edit crontab**:
   ```bash
   crontab -e
   ```

4. **Add schedule** (example: daily at 2 AM):
   ```cron
   0 2 * * * /full/path/to/garmin-connect-sync/cron/sync-cron.sh
   ```

5. **Verify cron**:
   ```bash
   crontab -l
   ```

6. **Check cron logs**:
   ```bash
   tail -f logs/cron-sync.log
   ```

### Systemd Timer (Alternative)

Create `~/.config/systemd/user/garmin-sync.service`:

```ini
[Unit]
Description=Garmin Connect Sync
After=network.target

[Service]
Type=oneshot
ExecStart=/path/to/garmin-connect-sync/cron/sync-cron.sh
```

Create `~/.config/systemd/user/garmin-sync.timer`:

```ini
[Unit]
Description=Daily Garmin Connect Sync

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
systemctl --user enable garmin-sync.timer
systemctl --user start garmin-sync.timer
systemctl --user list-timers
```

## NAS Deployment

### Synology NAS

1. **Install Docker** via Package Center

2. **Enable SSH** (Control Panel > Terminal & SNMP)

3. **SSH to NAS**:
   ```bash
   ssh admin@your-nas-ip
   ```

4. **Clone repository**:
   ```bash
   cd /volume1/docker/
   git clone <repository-url> garmin-connect-sync
   cd garmin-connect-sync
   ```

5. **Setup as above**, then:
   ```bash
   # Use sudo for docker commands on Synology
   sudo docker-compose up -d postgres
   sudo ./scripts/init_db.sh
   sudo docker-compose --profile sync run --rm garmin-sync --full
   ```

6. **Schedule Task** in DSM:
   - Control Panel > Task Scheduler
   - Create > Scheduled Task > User-defined script
   - Schedule: Daily at 2:00 AM
   - Script:
     ```bash
     cd /volume1/docker/garmin-connect-sync
     /usr/local/bin/docker-compose --profile sync run --rm garmin-sync
     ```

### QNAP NAS

Similar to Synology, using Container Station for Docker management.

### Ugreen NAS

1. Install Docker via app store
2. Use SSH or terminal for setup
3. Follow standard Docker deployment steps

## Verification Checklist

After setup, verify:

- [ ] PostgreSQL is running: `docker-compose ps`
- [ ] Database schema created: Tables exist
- [ ] Garmin tokens valid: Located in correct directory
- [ ] First sync completed: Data in database
- [ ] Automation configured: Cron/timer set up
- [ ] Logs accessible: Can view sync logs
- [ ] Backup script works: Test `./scripts/backup_db.sh`

## Next Steps

1. Review [SCHEMA.md](SCHEMA.md) to understand the database structure
2. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if you encounter issues
3. Customize queries for your data analysis needs
4. Set up regular database backups
5. Monitor disk space usage

## Support

If you encounter issues:
1. Check logs in `logs/` directory
2. Verify database connection
3. Ensure Garmin tokens are valid (re-authenticate if needed)
4. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
