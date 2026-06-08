-- Road marathon support on race_targets.
--
-- discipline: 'trail' (default, backward-compatible) | 'road'. Drives the
--   road-marathon engine path (pace_calculator, MPR sessions, 35 km LR cap).
-- target_time_seconds: optional goal finish time (e.g. 12600 = 3h30) used to
--   flag an overly optimistic objective in pace_calculator.
--
-- Applied manually (see spec 02 §12). Do NOT auto-apply to prod.
ALTER TABLE race_targets ADD COLUMN IF NOT EXISTS discipline VARCHAR(20) NOT NULL DEFAULT 'trail';
ALTER TABLE race_targets ADD COLUMN IF NOT EXISTS target_time_seconds INTEGER;
