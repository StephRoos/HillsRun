# Configuration Guide

This directory contains the configuration files for the Garmin Connect sync application.

## Quick Start

1. Copy the example configuration:
   ```bash
   cp config.yaml.example config.yaml
   ```

2. Edit `config.yaml` and set your database password:
   ```yaml
   database:
     password: your_secure_password_here
   ```

3. Ensure your Garmin tokens are available in `~/.garminconnect`

## Configuration Options

### Database

- **host**: Database hostname (`postgres` in Docker, `localhost` for local)
- **port**: Database port (default: 5432)
- **database**: Database name
- **user**: Database username
- **password**: Database password (use environment variable for security)
- **pool_min_size**: Minimum connection pool size
- **pool_max_size**: Maximum connection pool size

### Garmin

- **tokens_dir**: Path to Garmin OAuth tokens directory
  - Default: `~/.garminconnect`
  - Must contain valid OAuth tokens from garminconnect library
  - Tokens are valid for ~1 year

### Sync

- **categories**: List of data categories to synchronize
  - `daily_health`: Steps, calories, heart rate, sleep, stress, body battery
  - `activities`: Sports activities (running, cycling, swimming, etc.)
  - `body_composition`: Weight, BMI, body fat, muscle mass
  - `advanced_metrics`: HRV, SpO2, VO2 Max, respiration, training readiness
  - `wellness`: Hydration, additional wellness data

- **mode**: Synchronization mode
  - `incremental`: Only sync new data since last sync (recommended)
  - `full`: Sync all data within the `days_back` window

- **days_back**: Number of days to look back for full sync (default: 90)

- **rate_limit_delay**: Delay between API calls in seconds
  - Recommended: 0.5-1.0 seconds
  - Prevents hitting Garmin Connect API rate limits

### Logging

- **level**: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **log_dir**: Directory for log files
- **log_to_console**: Enable console output
- **log_to_file**: Enable file logging with rotation

## Environment Variables

You can override any configuration value using environment variables:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `GARMIN_TOKENS_DIR`
- `LOG_LEVEL`

Environment variables take precedence over config file values.

## Docker Configuration

When running in Docker, use these settings in `config.yaml`:

```yaml
database:
  host: postgres  # Docker service name
  password: ${POSTGRES_PASSWORD}  # From .env file

garmin:
  tokens_dir: /tokens  # Mounted volume in container
```

And in your `.env` file:
```
POSTGRES_PASSWORD=your_secure_password
GARMIN_TOKENS_DIR=/path/to/your/tokens
```

## Security Best Practices

1. **Never commit `config.yaml` with secrets** - Use environment variables
2. **Use strong database passwords**
3. **Mount Garmin tokens as read-only** in Docker
4. **Keep tokens secure** - They provide full access to your Garmin account
5. **Rotate tokens periodically** - Re-authenticate every 6-12 months
