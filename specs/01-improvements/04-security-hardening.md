# Task 04: Security Hardening

## Context
Several security items flagged in CLAUDE.md need resolution before HillsRun can be considered production-ready for multi-user deployment.

## Scope
- Rotate `BETTER_AUTH_SECRET` (currently using dev value)
- Rotate `GARMIN_API_KEY`
- Audit environment variable handling
- Ensure no secrets in git history
- Add `.env.example` with documented variables (no real values)

## Implementation Details

### Files to Create/Modify
- `web/.env.example` — Document all required frontend env vars
- `.env.example` — Document all required backend env vars
- `web/src/lib/auth.ts` — Verify secret loaded from env only
- `src/api/auth.py` — Verify API key loaded from env only

### Key Functionality
- Generate new `BETTER_AUTH_SECRET` (32+ chars random)
- Generate new `GARMIN_API_KEY`
- Update deployed instances (NAS + Vercel) with new values
- Verify old sessions are invalidated after secret rotation
- Check git history for any committed secrets (git log -p | grep -i secret)

### Technologies Used
- openssl rand -base64 32 (key generation)
- Vercel env vars dashboard
- Docker env_file

## Success Criteria
- [ ] New `BETTER_AUTH_SECRET` deployed and working
- [ ] New `GARMIN_API_KEY` deployed and working
- [ ] `.env.example` exists in both root and web/ with all vars documented
- [ ] No real secrets in git history
- [ ] App still works after rotation

## Dependencies
**Must complete first**: None
**Blocks**: None

## Related Documentation
- **CLAUDE.md**: Known Issues

---
**Estimated Time**: 1 hour
**Phase**: Core
