# Garmin Connect to PostgreSQL Sync

Automatic synchronization of Garmin Connect data (health, activities, body composition, and advanced metrics) to a PostgreSQL database.

## Features

- **Comprehensive Data Sync**: Health metrics, activities, body composition, advanced metrics, and wellness data
- **Incremental & Full Sync**: Smart incremental updates or full historical syncs
- **Docker Deployment**: Easy deployment with Docker Compose on any server or NAS
- **Automated Scheduling**: Built-in cron support for daily automated syncs
- **Robust Error Handling**: Retry logic, graceful degradation, detailed logging
- **PostgreSQL Storage**: Optimized schema with proper indexes and JSONB support

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Garmin Connect account with valid OAuth tokens
- PostgreSQL 15+ (provided via Docker)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd garmin-connect-sync

# Create environment file
cp .env.example .env
# Edit .env and set your POSTGRES_PASSWORD

# Create configuration
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml as needed
```

### 2. Authenticate with Garmin

First, authenticate once to get OAuth tokens:

```bash
# Install garminconnect locally
pip install garminconnect

# Authenticate (tokens will be saved to ~/.garminconnect)
python -c "from garminconnect import Garmin; import garth; garth.login('your.email@example.com', 'your_password'); garth.save('~/.garminconnect')"
```

Tokens are valid for ~1 year.

### 3. Initialize Database

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready (about 10 seconds)
sleep 10

# Initialize database schema
./scripts/init_db.sh
```

### 4. Run First Sync

```bash
# Full sync (last 90 days by default)
docker-compose --profile sync run --rm garmin-sync --full

# Or incremental sync
docker-compose --profile sync run --rm garmin-sync
```

### 5. Setup Automated Sync (Optional)

```bash
# Make cron script executable
chmod +x cron/sync-cron.sh

# Add to crontab
crontab -e
# Add line (adjust path):
0 2 * * * /path/to/garmin-connect-sync/cron/sync-cron.sh
```

## Data Categories

### Daily Health
- Steps, distance, calories (active, BMR, total)
- Floors climbed/descended
- Heart rate (min, max, resting, average, intraday samples)
- Stress levels (average, max, intraday chart)
- Sleep data (deep, light, REM, awake, sleep score)
- Body battery (charged, drained, intraday values)
- Intensity minutes (moderate, vigorous)

### Activities
- All sports activities (running, cycling, swimming, etc.)
- Comprehensive metrics: speed, pace, heart rate, cadence, power
- Training effects (aerobic, anaerobic)
- Elevation data
- Running dynamics (vertical oscillation, ground contact time, stride length)
- Activity splits/laps

### Body Composition
- Weight, BMI
- Body fat percentage
- Muscle mass, bone mass
- Body water percentage
- Metabolic age, visceral fat rating
- Basal and active metabolic rate

### Advanced Metrics
- HRV (Heart Rate Variability)
- SpO2 (blood oxygen saturation)
- VO2 Max (running, cycling)
- Fitness age
- Lactate threshold
- Respiration rate

### Wellness
- Hydration tracking
- Additional wellness metrics

## Usage

### Command Line Options

```bash
# Show what would be synced (dry run)
docker-compose --profile sync run --rm garmin-sync --dry-run

# Sync specific categories
docker-compose --profile sync run --rm garmin-sync --categories daily_health activities

# Sync specific date range
docker-compose --profile sync run --rm garmin-sync --start-date 2024-01-01 --end-date 2024-01-31

# Full sync with custom days back
docker-compose --profile sync run --rm garmin-sync --full --days-back 180

# Override log level
docker-compose --profile sync run --rm garmin-sync --log-level DEBUG
```

### Manual Python Execution

```bash
python main.py --help
python main.py --config config/config.yaml --full
```

## Database Schema

The application creates the following main tables:

- `garmin_user`: User profile
- `sync_state`: Sync tracking per category
- `daily_summary`: Daily health summary
- `heart_rate_samples`: Intraday heart rate
- `sleep_data`: Sleep metrics
- `stress_data`: Stress levels
- `body_battery`: Energy levels
- `body_composition`: Weight and body metrics
- `hrv_data`, `spo2_data`, `fitness_metrics`, `respiration_data`: Advanced metrics
- `activities`: Sports activities
- `activity_splits`: Activity laps/splits
- `hydration_data`: Hydration tracking

See [docs/SCHEMA.md](docs/SCHEMA.md) for detailed schema documentation.

## Configuration

Configuration is managed via `config/config.yaml` and environment variables.

Key settings:
- **Database**: Connection settings, pooling
- **Garmin**: Tokens directory
- **Sync**: Categories, mode (incremental/full), days back, rate limiting
- **Logging**: Level, file output

See [config/README.md](config/README.md) for full configuration guide.

## Architecture

```
┌─────────────────────────────────────┐
│     Garmin Connect API              │
└──────────────┬──────────────────────┘
               │ OAuth Tokens
┌──────────────▼──────────────────────┐
│   GarminClient (Python)             │
│   ├── Rate Limiting                 │
│   ├── Retry Logic                   │
│   └── Error Handling                │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   SyncManager                       │
│   ├── DailyHealthFetcher            │
│   ├── ActivitiesFetcher             │
│   ├── BodyCompositionFetcher        │
│   ├── AdvancedMetricsFetcher        │
│   └── WellnessFetcher               │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   PostgreSQL Database               │
│   ├── Optimized Schema              │
│   ├── JSONB for Complex Data        │
│   └── Sync State Tracking           │
└─────────────────────────────────────┘
```

## Maintenance

### Backups

```bash
# Create backup
./scripts/backup_db.sh

# Backups are stored in backups/ directory
```

### View Logs

```bash
# Application logs
ls -la logs/

# Cron logs
tail -f logs/cron-sync.log

# Docker logs
docker-compose logs garmin-sync
```

### Check Sync Status

```sql
-- Connect to database
psql -h localhost -U garmin -d garmin_connect

-- View sync state
SELECT * FROM sync_state ORDER BY last_sync_timestamp DESC;

-- Count records per table
SELECT 'daily_summary' as table_name, COUNT(*) FROM daily_summary
UNION ALL
SELECT 'activities', COUNT(*) FROM activities
UNION ALL
SELECT 'body_composition', COUNT(*) FROM body_composition;
```

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

Common issues:
- **Authentication errors**: Re-authenticate with Garmin
- **Rate limiting**: Increase `rate_limit_delay` in config
- **Missing data**: Some features may not be available for all accounts
- **Database connection errors**: Check PostgreSQL is running and credentials are correct

## Development

### Requirements

- Python 3.11+
- PostgreSQL 15+
- Dependencies listed in `requirements.txt`

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py --config config/config.yaml
```

### Testing

```bash
# Dry run to test without writing
python main.py --dry-run

# Test specific category
python main.py --categories daily_health --start-date 2024-01-01 --end-date 2024-01-01
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Your chosen license]

## REST API

A read-only REST API (FastAPI) exposes all synced data over HTTP, secured by API key.

### Start the API

```bash
# Add API_KEY to your .env (see .env.example)
echo "API_KEY=your_secret_key" >> .env

# Build and start
docker-compose build garmin-api
docker-compose up -d garmin-api
```

### Endpoints

All endpoints are `GET`, authenticated via `X-API-Key` header (except `/health`).
Default date range: last 30 days. Pagination: `?limit=50&offset=0` (max limit 200).

| Route | Description |
|-------|-------------|
| `GET /health` | Health check (no auth) |
| `GET /api/v1/daily/summary` | Daily health summary |
| `GET /api/v1/daily/heart-rate` | Intraday heart rate samples |
| `GET /api/v1/daily/sleep` | Sleep data |
| `GET /api/v1/daily/stress` | Stress levels |
| `GET /api/v1/daily/body-battery` | Body battery |
| `GET /api/v1/body/composition` | Weight, BMI, body fat/muscle |
| `GET /api/v1/metrics/hrv` | Heart rate variability |
| `GET /api/v1/metrics/spo2` | Blood oxygen |
| `GET /api/v1/metrics/fitness` | VO2 Max, fitness age |
| `GET /api/v1/metrics/respiration` | Respiration rate |
| `GET /api/v1/activities` | Activities list (filter: `sport_type`, `activity_type`) |
| `GET /api/v1/activities/{id}` | Activity detail |
| `GET /api/v1/activities/{id}/splits` | Activity laps/splits |
| `GET /api/v1/wellness/hydration` | Hydration |
| `GET /api/v1/sync/status` | Sync state per category |

### Example

```bash
# Health check
curl http://localhost:8100/health

# Last 7 days of activities
curl -H "X-API-Key: your_key" \
  "http://localhost:8100/api/v1/activities?start_date=2026-02-10&end_date=2026-02-17"

# Paginated daily summary
curl -H "X-API-Key: your_key" \
  "http://localhost:8100/api/v1/daily/summary?limit=10&offset=0"
```

Swagger UI available at `http://localhost:8100/docs`.

### HTTPS via NAS reverse proxy

Configure the NAS reverse proxy:
- Source: `https://your-domain.com` (port 443)
- Destination: `http://localhost:8100`

The NAS manages the SSL certificate (Let's Encrypt).

See [docs/PLAN-API.md](docs/PLAN-API.md) for the full API implementation plan.

---

## Current Deployment

Successfully deployed on **Ugreen NAS** (ARM64) with automated daily sync:

- **Host**: `192.168.129.21`, PostgreSQL on port `15432`
- **Sync schedule**: Daily at 06:00 (Europe/Paris) via Docker scheduler
- **Data**: 90 days of historical data across all 5 categories (387 records, 63k+ heart rate samples)

See [docs/SETUP.md](docs/SETUP.md#ugreen-nas-tested--deployed) for full NAS deployment guide.

## Acknowledgments

- Built with [python-garminconnect](https://github.com/cyberjunky/python-garminconnect)
- Uses [asyncpg](https://github.com/MagicStack/asyncpg) for PostgreSQL
- Deployed with Docker

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- Review logs in `logs/` directory
