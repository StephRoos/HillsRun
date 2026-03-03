# Database Schema Documentation

Complete documentation of the PostgreSQL database schema for Garmin Connect data.

## Overview

The database uses PostgreSQL 15+ with the following features:
- **JSONB** for complex/variable data structures
- **TIMESTAMPTZ** for proper timezone handling
- **Optimized indexes** for common query patterns
- **UPSERT** support via `ON CONFLICT` clauses
- **Automatic timestamps** via triggers

## Schema Diagram

```
garmin_user (1) ──── (N) daily_summary
            │
            ├──── (N) heart_rate_samples
            │
            ├──── (N) sleep_data
            │
            ├──── (N) stress_data
            │
            ├──── (N) body_battery
            │
            ├──── (N) body_composition
            │
            ├──── (N) hrv_data
            │
            ├──── (N) spo2_data
            │
            ├──── (N) fitness_metrics
            │
            ├──── (N) respiration_data
            │
            ├──── (N) hydration_data
            │
            └──── (N) activities (1) ──── (N) activity_splits
```

## Core Tables

### `garmin_user`

Stores Garmin user profile information.

| Column | Type | Description |
|--------|------|-------------|
| user_id | BIGSERIAL | Primary key (internal) |
| garmin_user_id | VARCHAR(100) | Garmin's user ID (unique) |
| display_name | VARCHAR(255) | User's display name |
| email | VARCHAR(255) | User's email |
| profile_image_url | TEXT | Profile picture URL |
| created_at | TIMESTAMPTZ | Record creation time |
| updated_at | TIMESTAMPTZ | Last update time |

**Indexes**: garmin_user_id (unique)

### `sync_state`

Tracks synchronization state per category.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| category | VARCHAR(50) | Sync category (unique) |
| last_sync_date | DATE | Last successfully synced date |
| last_sync_timestamp | TIMESTAMPTZ | When sync occurred |
| records_synced | INTEGER | Number of records in last sync |
| sync_status | VARCHAR(20) | Status: success, partial, failed |
| error_message | TEXT | Error details if failed |

**Valid categories**: daily_health, activities, body_composition, advanced_metrics, wellness

**Indexes**: category (unique)

## Daily Health Tables

### `daily_summary`

Daily health and activity summary.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date of summary |
| total_steps | INTEGER | Total steps |
| step_goal | INTEGER | Daily step goal |
| total_distance_meters | NUMERIC(10,2) | Distance in meters |
| active_calories | INTEGER | Active calories burned |
| bmr_calories | INTEGER | Basal metabolic rate calories |
| total_calories | INTEGER | Total calories burned |
| floors_ascended | NUMERIC(5,1) | Floors climbed |
| floors_descended | NUMERIC(5,1) | Floors descended |
| floors_goal | INTEGER | Daily floor goal |
| moderate_intensity_minutes | INTEGER | Moderate activity minutes |
| vigorous_intensity_minutes | INTEGER | Vigorous activity minutes |
| intensity_minutes_goal | INTEGER | Intensity minutes goal |
| highly_active_seconds | INTEGER | Time in high activity |
| active_seconds | INTEGER | Time in active state |
| sedentary_seconds | INTEGER | Time sedentary |
| sleeping_seconds | INTEGER | Time sleeping |
| max_heart_rate | INTEGER | Max HR for the day |
| min_heart_rate | INTEGER | Min HR for the day |
| resting_heart_rate | INTEGER | Resting HR |
| average_heart_rate | INTEGER | Average HR |
| average_stress_level | INTEGER | Average stress (0-100) |
| max_stress_level | INTEGER | Max stress level |
| stress_qualifier | VARCHAR(50) | Stress description |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)
**Indexes**: (user_id, calendar_date DESC), calendar_date DESC

### `heart_rate_samples`

Intraday heart rate measurements.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| timestamp | TIMESTAMPTZ | Sample timestamp |
| heart_rate | INTEGER | Heart rate (bpm) |
| created_at | TIMESTAMPTZ | Record creation |

**Unique constraint**: (user_id, timestamp)
**Indexes**: (user_id, timestamp DESC)

**Note**: Can generate large volume of data. Consider retention policy.

### `sleep_data`

Daily sleep metrics and sleep stages.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Sleep date |
| sleep_start_timestamp | TIMESTAMPTZ | Sleep start time |
| sleep_end_timestamp | TIMESTAMPTZ | Sleep end time |
| total_sleep_seconds | INTEGER | Total sleep duration |
| deep_sleep_seconds | INTEGER | Deep sleep duration |
| light_sleep_seconds | INTEGER | Light sleep duration |
| rem_sleep_seconds | INTEGER | REM sleep duration |
| awake_seconds | INTEGER | Time awake during sleep |
| sleep_score | INTEGER | Sleep quality score (0-100) |
| sleep_quality | VARCHAR(50) | Quality descriptor |
| sleep_levels | JSONB | Detailed sleep stage data |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)
**Indexes**: (user_id, calendar_date DESC), GIN on sleep_levels

### `stress_data`

Daily stress levels and breakdowns.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date |
| average_stress_level | INTEGER | Average stress (0-100) |
| max_stress_level | INTEGER | Peak stress level |
| rest_stress_duration_seconds | INTEGER | Rest stress time |
| activity_stress_duration_seconds | INTEGER | Activity stress time |
| uncategorized_stress_duration_seconds | INTEGER | Uncategorized time |
| low_stress_duration_seconds | INTEGER | Low stress time |
| medium_stress_duration_seconds | INTEGER | Medium stress time |
| high_stress_duration_seconds | INTEGER | High stress time |
| stress_chart_values | JSONB | Intraday stress samples |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)

### `body_battery`

Daily energy level tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date |
| charged_value | INTEGER | Energy gained |
| drained_value | INTEGER | Energy lost |
| highest_value | INTEGER | Peak energy (0-100) |
| lowest_value | INTEGER | Lowest energy |
| start_timestamp | TIMESTAMPTZ | Day start |
| end_timestamp | TIMESTAMPTZ | Day end |
| body_battery_values | JSONB | Intraday energy samples |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)

## Body Composition Tables

### `body_composition`

Weight and body metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| timestamp | TIMESTAMPTZ | Measurement time |
| weight_kg | NUMERIC(6,2) | Weight in kilograms |
| bmi | NUMERIC(5,2) | Body Mass Index |
| body_fat_percentage | NUMERIC(5,2) | Body fat % |
| body_water_percentage | NUMERIC(5,2) | Body water % |
| bone_mass_kg | NUMERIC(5,2) | Bone mass |
| muscle_mass_kg | NUMERIC(6,2) | Muscle mass |
| metabolic_age | INTEGER | Metabolic age |
| visceral_fat_rating | INTEGER | Visceral fat level |
| basal_met | NUMERIC(7,2) | Basal metabolic rate |
| active_met | NUMERIC(7,2) | Active metabolic rate |
| physique_rating | INTEGER | Physique rating |
| source_type | VARCHAR(50) | Source (scale, manual, etc.) |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, timestamp)
**Indexes**: (user_id, timestamp DESC)

## Advanced Metrics Tables

### `hrv_data`

Heart Rate Variability metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date |
| weekly_avg | NUMERIC(6,2) | 7-day average HRV |
| last_night_avg | NUMERIC(6,2) | Last night average |
| last_night_5_min_high | NUMERIC(6,2) | Peak 5-min average |
| hrv_status | VARCHAR(50) | Status (balanced, low, etc.) |
| feedback_phrase | TEXT | Feedback message |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)

### `spo2_data`

Blood oxygen saturation.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date |
| average_spo2_percentage | NUMERIC(5,2) | Average SpO2 |
| lowest_spo2_percentage | NUMERIC(5,2) | Lowest SpO2 |
| latest_spo2_reading | NUMERIC(5,2) | Most recent reading |
| latest_spo2_reading_timestamp | TIMESTAMPTZ | Time of latest reading |
| spo2_values | JSONB | Intraday SpO2 samples |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)

### `fitness_metrics`

VO2 Max, fitness age, and related metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date |
| vo2_max | NUMERIC(5,2) | Overall VO2 Max |
| vo2_max_running | NUMERIC(5,2) | Running VO2 Max |
| vo2_max_cycling | NUMERIC(5,2) | Cycling VO2 Max |
| fitness_age | INTEGER | Fitness age estimate |
| lactate_threshold_bpm | INTEGER | Lactate threshold HR |
| lactate_threshold_speed | NUMERIC(5,2) | LT speed |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)

### `respiration_data`

Breathing rate measurements.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date |
| avg_waking_respiration_rate | NUMERIC(5,2) | Awake breathing rate |
| max_waking_respiration_rate | NUMERIC(5,2) | Max awake rate |
| min_waking_respiration_rate | NUMERIC(5,2) | Min awake rate |
| avg_sleep_respiration_rate | NUMERIC(5,2) | Sleep breathing rate |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)

## Activities Tables

### `activities`

Sports and fitness activities.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| activity_id | BIGINT | Garmin activity ID (unique) |
| activity_name | VARCHAR(255) | Activity name |
| activity_type | VARCHAR(100) | Type (running, cycling, etc.) |
| sport_type | VARCHAR(100) | Specific sport |
| start_timestamp | TIMESTAMPTZ | Start time |
| duration_seconds | INTEGER | Duration |
| distance_meters | NUMERIC(10,2) | Distance |
| average_speed | NUMERIC(8,4) | Average speed (m/s) |
| max_speed | NUMERIC(8,4) | Max speed |
| average_pace | NUMERIC(8,4) | Average pace (min/km) |
| max_pace | NUMERIC(8,4) | Max pace |
| calories | INTEGER | Calories burned |
| average_hr | INTEGER | Average heart rate |
| max_hr | INTEGER | Max heart rate |
| average_running_cadence | NUMERIC(6,2) | Avg cadence (running) |
| max_running_cadence | INTEGER | Max cadence |
| average_bike_cadence | NUMERIC(6,2) | Avg cadence (cycling) |
| max_bike_cadence | INTEGER | Max cadence |
| average_power | NUMERIC(8,2) | Average power (watts) |
| max_power | INTEGER | Max power |
| normalized_power | NUMERIC(8,2) | Normalized power |
| training_stress_score | NUMERIC(6,2) | TSS |
| intensity_factor | NUMERIC(4,3) | IF |
| elevation_gain_meters | NUMERIC(8,2) | Elevation gain |
| elevation_loss_meters | NUMERIC(8,2) | Elevation loss |
| min_elevation_meters | NUMERIC(8,2) | Min elevation |
| max_elevation_meters | NUMERIC(8,2) | Max elevation |
| average_temperature | NUMERIC(5,2) | Avg temperature (°C) |
| max_temperature | NUMERIC(5,2) | Max temperature |
| min_temperature | NUMERIC(5,2) | Min temperature |
| training_effect | NUMERIC(3,1) | Overall training effect |
| aerobic_training_effect | NUMERIC(3,1) | Aerobic TE |
| anaerobic_training_effect | NUMERIC(3,1) | Anaerobic TE |
| avg_vertical_oscillation | NUMERIC(6,2) | Vertical oscillation (cm) |
| avg_ground_contact_time | INTEGER | Ground contact time (ms) |
| avg_stride_length | NUMERIC(6,2) | Stride length (m) |
| vo2_max_value | NUMERIC(5,2) | VO2 Max from activity |
| lactate_threshold_bpm | INTEGER | LT heart rate |
| device_name | VARCHAR(100) | Recording device |
| description | TEXT | Activity description |
| manual_activity | BOOLEAN | Manually entered |
| pr | BOOLEAN | Personal record |
| favorite | BOOLEAN | Marked favorite |
| auto_calc_calories | BOOLEAN | Auto-calculated calories |
| num_laps | INTEGER | Number of laps |
| activity_data | JSONB | Full activity JSON |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: activity_id
**Indexes**:
- (user_id, start_timestamp DESC)
- start_timestamp DESC
- activity_type
- sport_type
- GIN on activity_data
- Partial: PR activities, favorites, manual activities

### `activity_splits`

Laps and splits within activities.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| activity_id | BIGINT | FK to activities |
| split_index | INTEGER | Split number (0-based) |
| split_type | VARCHAR(50) | Type (lap, auto, manual) |
| distance_meters | NUMERIC(10,2) | Split distance |
| duration_seconds | INTEGER | Split duration |
| average_speed | NUMERIC(8,4) | Average speed |
| average_hr | INTEGER | Average HR |
| max_hr | INTEGER | Max HR |
| average_power | NUMERIC(8,2) | Average power |
| max_power | INTEGER | Max power |
| average_cadence | NUMERIC(6,2) | Average cadence |
| elevation_gain_meters | NUMERIC(8,2) | Elevation gain |
| elevation_loss_meters | NUMERIC(8,2) | Elevation loss |
| start_timestamp | TIMESTAMPTZ | Split start |
| created_at | TIMESTAMPTZ | Record creation |

**Unique constraint**: (activity_id, split_index)
**Indexes**: activity_id

## Wellness Tables

### `hydration_data`

Water intake tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to garmin_user |
| calendar_date | DATE | Date |
| total_hydration_ml | INTEGER | Total water consumed (ml) |
| hydration_goal_ml | INTEGER | Daily goal |
| hydration_entries | JSONB | Individual log entries |
| created_at | TIMESTAMPTZ | Record creation |
| updated_at | TIMESTAMPTZ | Last update |

**Unique constraint**: (user_id, calendar_date)

## Utility Functions

### `get_or_create_user()`

Gets existing user or creates new one.

```sql
SELECT get_or_create_user('garmin_user_id', 'Display Name', 'email@example.com');
```

### `get_last_sync_date()`

Retrieves last sync date for a category.

```sql
SELECT get_last_sync_date('daily_health');
```

### `upsert_sync_state()`

Updates sync state after synchronization.

```sql
SELECT upsert_sync_state('daily_health', '2024-01-15', 100, 'success', NULL);
```

## Views

### `recent_activities_summary`

Quick overview of recent activities.

```sql
SELECT * FROM recent_activities_summary LIMIT 10;
```

### `weekly_health_trends`

Weekly aggregation of health metrics.

```sql
SELECT * FROM weekly_health_trends WHERE user_id = 1 ORDER BY week_start DESC;
```

## Example Queries

### Get daily steps for last 30 days

```sql
SELECT calendar_date, total_steps, step_goal
FROM daily_summary
WHERE user_id = 1
  AND calendar_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY calendar_date DESC;
```

### Activities by type with totals

```sql
SELECT
    activity_type,
    COUNT(*) as count,
    SUM(distance_meters) / 1000.0 as total_km,
    SUM(duration_seconds) / 3600.0 as total_hours,
    SUM(calories) as total_calories
FROM activities
WHERE user_id = 1
GROUP BY activity_type
ORDER BY count DESC;
```

### Sleep quality trend

```sql
SELECT
    calendar_date,
    total_sleep_seconds / 3600.0 as hours,
    sleep_score,
    deep_sleep_seconds / 3600.0 as deep_hours,
    rem_sleep_seconds / 3600.0 as rem_hours
FROM sleep_data
WHERE user_id = 1
  AND calendar_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY calendar_date DESC;
```

### Weight trend

```sql
SELECT
    timestamp::date as date,
    weight_kg,
    body_fat_percentage,
    muscle_mass_kg,
    bmi
FROM body_composition
WHERE user_id = 1
ORDER BY timestamp DESC
LIMIT 30;
```

## Maintenance

### Vacuum and analyze

```sql
VACUUM ANALYZE;
```

### Check table sizes

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## athlete_profiles — Day Preferences Column

```sql
-- Added by sql/10_day_preferences.sql
ALTER TABLE athlete_profiles ADD COLUMN IF NOT EXISTS day_preferences JSONB;
```

**JSONB structure**:
```json
{
  "long_run": 7,
  "quality": [2, 4],
  "easy_run": [1, 5],
  "strength": [1, 5]
}
```

| Key | Type | Description |
|-----|------|-------------|
| `long_run` | int (1-7) | Preferred day for weekly long run |
| `quality` | int[] (max 3) | Preferred days for hard sessions (tempo, intervals, hill repeats) |
| `easy_run` | int[] (max 5) | Preferred days for easy/recovery runs |
| `strength` | int[] (max 2) | Preferred days for cross-training (RMU) |

Day numbers follow ISO convention: 1=Monday, 7=Sunday. All fields nullable.

---

### Clean old heart rate samples

```sql
DELETE FROM heart_rate_samples
WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 year';

VACUUM FULL heart_rate_samples;
```
