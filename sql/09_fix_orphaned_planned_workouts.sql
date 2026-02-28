-- Fix orphaned planned workouts left by training plan deletion (ON DELETE SET NULL)
-- and change FK to CASCADE so future deletions clean up automatically.

-- Step 1: Delete orphaned planned workouts (plan was deleted, plan_id set to NULL)
DELETE FROM planned_workouts
WHERE plan_id IS NULL AND session_type IS NOT NULL;

-- Step 2: Change FK from ON DELETE SET NULL to ON DELETE CASCADE
ALTER TABLE planned_workouts
    DROP CONSTRAINT IF EXISTS planned_workouts_plan_id_fkey;

ALTER TABLE planned_workouts
    ADD CONSTRAINT planned_workouts_plan_id_fkey
    FOREIGN KEY (plan_id) REFERENCES training_plans(id) ON DELETE CASCADE;
