# Task 03: Fix Scheduler DB Constraints

## Context
The automated daily sync scheduler is currently disabled because of broken `ON CONFLICT` DB constraints. This forces users to manually trigger sync or rely on the auto-sync-on-login hook. Fixing this restores fully automated daily data updates.

## Scope
- Diagnose the exact DB constraint conflicts in the scheduler path
- Write SQL migration to fix affected constraints
- Re-enable scheduled sync (daily at 06:00 Europe/Paris)
- Verify incremental sync works without manual intervention

## Implementation Details

### Files to Modify
- `src/database.py` — Fix `ON CONFLICT` clauses for affected tables
- `sql/` — Add migration script for constraint fixes
- `docker-compose.yml` — Re-enable scheduler service or cron job
- `config/config.yaml` — Verify sync categories and schedule

### Key Functionality
- Identify which tables have broken `ON CONFLICT` (likely `training_readiness` or newer tables)
- Ensure all upsert methods handle new columns gracefully
- Test incremental sync for each of the 5 categories
- Add error recovery so one failed category doesn't block others

### Technologies Used
- PostgreSQL (ALTER TABLE, constraints)
- asyncpg (upsert queries)
- Docker Compose (scheduler service)

## Success Criteria
- [ ] SQL migration applied without data loss
- [ ] `docker-compose run garmin-sync` completes for all 5 categories
- [ ] Incremental sync runs daily at 06:00 without errors for 3+ days
- [ ] Sync status shows "success" for all categories

## Dependencies
**Must complete first**: None
**Blocks**: None (independent improvement)

## Related Documentation
- **CLAUDE.md**: Known Issues section
- **docs/SCHEMA.md**: Table constraints

---
**Estimated Time**: 2 hours
**Phase**: Core
