# Troubleshooting Guide

Common issues and solutions for the Garmin Connect sync application.

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [Database Connection Issues](#database-connection-issues)
3. [Sync Failures](#sync-failures)
4. [Missing Data](#missing-data)
5. [Performance Issues](#performance-issues)
6. [Docker Issues](#docker-issues)

---

## Authentication Issues

### Error: "Garmin tokens not found"

**Symptom**: Application fails with "FileNotFoundError: Garmin tokens not found"

**Causes**:
- Tokens not created yet
- Tokens in wrong directory
- Incorrect path configuration

**Solutions**:

1. **Authenticate with Garmin**:
   ```bash
   pip install garminconnect
   python3 << 'EOF'
   import garth
   garth.login('your.email@example.com', 'your_password')
   garth.save('~/.garminconnect')
   EOF
   ```

2. **Verify tokens exist**:
   ```bash
   ls -la ~/.garminconnect/
   # Should see oauth1_token.json and oauth2_token.json
   ```

3. **Check configuration**:
   ```yaml
   # config/config.yaml
   garmin:
     tokens_dir: ~/.garminconnect  # Ensure correct path
   ```

4. **For Docker**, ensure tokens are mounted:
   ```yaml
   # docker-compose.yml
   volumes:
     - ${GARMIN_TOKENS_DIR:-~/.garminconnect}:/tokens:ro
   ```

### Error: "401 Unauthorized"

**Symptom**: API calls fail with "Authentication required (401 Unauthorized)"

**Causes**:
- Expired tokens (>1 year old)
- Invalid tokens
- Garmin account password changed

**Solutions**:

1. **Re-authenticate**:
   ```bash
   rm -rf ~/.garminconnect/
   # Then authenticate again (see above)
   ```

2. **Verify Garmin account**:
   - Log into https://connect.garmin.com/
   - Ensure account is active

3. **Check for 2FA/MFA**:
   - If you enabled MFA after last auth, re-authenticate

### Error: "403 Forbidden"

**Symptom**: Specific endpoints return 403

**Causes**:
- Feature not available for your account type
- Geographic restrictions
- API endpoint access denied

**Solutions**:

1. **Check account features**:
   - Some metrics require specific Garmin devices
   - Verify data is visible in Garmin Connect web/app

2. **Try different category**:
   ```bash
   # Skip problematic categories
   docker-compose --profile sync run --rm garmin-sync \
     --categories daily_health activities
   ```

---

## Database Connection Issues

### Error: "Cannot connect to database"

**Symptom**: Application fails to connect to PostgreSQL

**Causes**:
- PostgreSQL not running
- Wrong connection parameters
- Network issues
- Password mismatch

**Solutions**:

1. **Check PostgreSQL status**:
   ```bash
   docker-compose ps postgres
   # Should show "healthy"
   ```

2. **Start PostgreSQL if stopped**:
   ```bash
   docker-compose up -d postgres
   sleep 10  # Wait for startup
   ```

3. **Verify credentials**:
   ```bash
   # Test connection
   docker-compose exec postgres psql -U garmin -d garmin_connect -c "SELECT 1"
   ```

4. **Check environment variables**:
   ```bash
   # Ensure .env has correct password
   cat .env | grep POSTGRES_PASSWORD
   ```

### Error: "Database does not exist"

**Symptom**: "FATAL: database 'garmin_connect' does not exist"

**Solutions**:

1. **Create database manually**:
   ```bash
   docker-compose exec postgres psql -U garmin -c "CREATE DATABASE garmin_connect;"
   ```

2. **Re-initialize**:
   ```bash
   ./scripts/init_db.sh
   ```

### Error: "Too many connections"

**Symptom**: "FATAL: sorry, too many clients already"

**Solutions**:

1. **Check connection pool size**:
   ```yaml
   # config/config.yaml
   database:
     pool_max_size: 10  # Reduce if needed
   ```

2. **Close idle connections**:
   ```sql
   -- Connect and check
   SELECT count(*) FROM pg_stat_activity WHERE datname = 'garmin_connect';

   -- Kill idle connections
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE datname = 'garmin_connect' AND state = 'idle';
   ```

---

## Sync Failures

### Error: "429 Too Many Requests"

**Symptom**: "Rate limit exceeded (429)"

**Causes**:
- Making API calls too quickly
- Multiple syncs running simultaneously

**Solutions**:

1. **Increase rate limit delay**:
   ```yaml
   # config/config.yaml
   sync:
     rate_limit_delay: 1.0  # Increase from 0.5
   ```

2. **Wait before retrying**:
   ```bash
   # Wait 15 minutes, then retry
   sleep 900
   docker-compose --profile sync run --rm garmin-sync
   ```

3. **Ensure only one sync runs at a time**:
   ```bash
   # Check for running syncs
   docker-compose ps

   # Kill if stuck
   docker-compose --profile sync down
   ```

### Partial Sync Success

**Symptom**: Some categories sync, others fail

**Causes**:
- Some data not available
- API endpoint issues
- Specific feature not enabled

**Solutions**:

1. **Check sync state**:
   ```sql
   SELECT * FROM sync_state WHERE sync_status != 'success';
   ```

2. **Review error messages**:
   ```bash
   tail -100 logs/garmin_sync_*.log | grep ERROR
   ```

3. **Retry failed categories**:
   ```bash
   docker-compose --profile sync run --rm garmin-sync \
     --categories <failed_category>
   ```

### Error: "Max retries exceeded"

**Symptom**: "RetryError: Max retries exceeded"

**Causes**:
- Network issues
- Garmin API down
- Persistent API errors

**Solutions**:

1. **Check Garmin Connect status**:
   - Visit https://connect.garmin.com/
   - Check if service is accessible

2. **Check network**:
   ```bash
   # Test connectivity
   ping connect.garmin.com
   curl -I https://connect.garmin.com/
   ```

3. **Wait and retry**:
   - Garmin API may be temporarily down
   - Wait 30-60 minutes and retry

---

## Missing Data

### No Data for Specific Dates

**Symptom**: Data missing for certain dates in database

**Causes**:
- No Garmin data for those dates (device not worn)
- Sync didn't cover that date range
- API returned empty results

**Solutions**:

1. **Check Garmin Connect web**:
   - Verify data exists in Garmin Connect
   - Some data only syncs from device

2. **Re-sync specific date range**:
   ```bash
   docker-compose --profile sync run --rm garmin-sync \
     --start-date 2024-01-01 --end-date 2024-01-31
   ```

3. **Force full sync**:
   ```bash
   docker-compose --profile sync run --rm garmin-sync --full
   ```

### Activities Missing Details

**Symptom**: Activities appear but missing metrics (heart rate, power, etc.)

**Causes**:
- Sensors not used during activity
- Data not uploaded from device
- API doesn't return all fields

**Solutions**:

1. **Sync device with Garmin Connect**:
   - Ensure your Garmin device has synced
   - Wait 10-15 minutes after device sync
   - Retry application sync

2. **Check activity in Garmin Connect**:
   - Verify metrics are visible there
   - Some fields may not be available via API

### Advanced Metrics Missing

**Symptom**: HRV, SpO2, or VO2 Max data missing

**Causes**:
- Device doesn't support these metrics
- Features not enabled
- Requires specific Garmin watch models

**Solutions**:

1. **Verify device capabilities**:
   - Check if your device supports the metric
   - Enable features in Garmin Connect app

2. **Check if data exists**:
   - View in Garmin Connect web/app
   - If not there, API won't have it

---

## Performance Issues

### Slow Sync Speed

**Symptom**: Sync takes very long to complete

**Causes**:
- Large date range
- Too much rate limiting
- Slow network
- Large number of activities

**Solutions**:

1. **Use incremental sync**:
   ```yaml
   sync:
     mode: incremental  # Instead of full
   ```

2. **Reduce rate limiting** (carefully):
   ```yaml
   sync:
     rate_limit_delay: 0.3  # From 0.5, but watch for 429 errors
   ```

3. **Sync in smaller date ranges**:
   ```bash
   # Sync one month at a time
   docker-compose --profile sync run --rm garmin-sync \
     --start-date 2024-01-01 --end-date 2024-01-31
   ```

### High Memory Usage

**Symptom**: Docker container uses excessive memory

**Solutions**:

1. **Reduce connection pool**:
   ```yaml
   database:
     pool_max_size: 5  # From 10
   ```

2. **Process fewer categories at once**:
   ```bash
   # Sync one category at a time
   docker-compose --profile sync run --rm garmin-sync \
     --categories daily_health
   ```

### Database Growing Large

**Symptom**: PostgreSQL storage usage increasing rapidly

**Causes**:
- JSONB fields storing large data
- Heart rate samples (high frequency data)
- Many activities with detailed data

**Solutions**:

1. **Check table sizes**:
   ```sql
   SELECT
     schemaname,
     tablename,
     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

2. **Clean old heart rate samples**:
   ```sql
   -- Delete samples older than 1 year
   DELETE FROM heart_rate_samples
   WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 year';

   VACUUM FULL heart_rate_samples;
   ```

3. **Regular maintenance**:
   ```sql
   VACUUM ANALYZE;
   ```

---

## Docker Issues

### Container Won't Start

**Symptom**: garmin-sync container fails to start

**Solutions**:

1. **Check logs**:
   ```bash
   docker-compose --profile sync logs garmin-sync
   ```

2. **Rebuild container**:
   ```bash
   docker-compose build garmin-sync
   ```

3. **Check dependencies**:
   ```bash
   # Ensure postgres is healthy
   docker-compose ps postgres
   ```

### Volume Mount Issues

**Symptom**: "Permission denied" or tokens not found in container

**Solutions**:

1. **Check volume mounts**:
   ```bash
   docker-compose config | grep -A 5 volumes
   ```

2. **Verify permissions**:
   ```bash
   ls -la ~/.garminconnect/
   # Should be readable
   ```

3. **Use absolute paths**:
   ```yaml
   # docker-compose.yml
   volumes:
     - /home/user/.garminconnect:/tokens:ro  # Not ~/
   ```

---

## Getting Help

If issues persist:

1. **Enable debug logging**:
   ```bash
   docker-compose --profile sync run --rm garmin-sync --log-level DEBUG
   ```

2. **Collect logs**:
   ```bash
   # Save recent logs
   tail -500 logs/garmin_sync_*.log > debug.log
   ```

3. **Check sync state**:
   ```sql
   SELECT * FROM sync_state ORDER BY last_sync_timestamp DESC;
   ```

4. **Open GitHub issue** with:
   - Error messages
   - Relevant log excerpts (remove sensitive data)
   - Steps to reproduce
   - System information (OS, Docker version)
