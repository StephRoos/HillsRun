-- Add day preferences column to athlete_profiles
-- Stores preferred days for each session category:
-- { "long_run": 7, "quality": [2, 4], "strength": 3 }
-- Values are ISO day numbers (1=Monday, 7=Sunday)

ALTER TABLE athlete_profiles ADD COLUMN IF NOT EXISTS day_preferences JSONB;
