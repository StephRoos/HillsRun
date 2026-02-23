# Task 02: Frontend Test Expansion (Vitest)

## Context
HillsRun frontend has 99 TypeScript files, 30+ components, 10 hooks — but only 3 test files (use-online-status, offline-indicator, utils). Vitest is already configured with jsdom environment and React Testing Library. Need to expand coverage significantly.

## Scope
Add unit tests for:
- All utility functions in `lib/utils.ts`
- All React Query hooks (with mocked garminApi)
- Key components (dashboard cards, activity metrics, trend charts config)
- API proxy route logic

## Implementation Details

### Files to Create/Modify
- `web/src/lib/__tests__/garmin-api.test.ts` — API wrapper methods, error handling, GarminNotConnectedError
- `web/src/lib/__tests__/garmin-user.test.ts` — Cache behavior, deduplication
- `web/src/hooks/__tests__/use-activities.test.ts` — Query keys, params serialization
- `web/src/hooks/__tests__/use-metrics.test.ts` — All 8 metric hooks
- `web/src/hooks/__tests__/use-trends.test.ts` — Weekly aggregation, gap filling, period calculation
- `web/src/hooks/__tests__/use-sync.test.ts` — Job polling, invalidation
- `web/src/hooks/__tests__/use-coaching.test.ts` — Invite codes, access control
- `web/src/components/dashboard/__tests__/weekly-summary.test.tsx` — Rendering with data
- `web/src/components/activity/__tests__/activity-metrics.test.tsx` — Metric formatting

### Key Functionality
- Mock `garminFetch` for all hook tests
- Test React Query hooks with `@tanstack/react-query` test utils
- Verify correct query keys and staleTime settings
- Test error states (GarminNotConnectedError, network errors)
- Test `useTrends` aggregation logic (most complex hook, 215 lines)

### Technologies Used
- Vitest (already configured)
- @testing-library/react (already installed)
- vi.mock for module mocking

## Success Criteria
- [ ] `pnpm test` passes in `web/`
- [ ] >60 new test cases
- [ ] All hooks have at least basic coverage
- [ ] `useTrends` aggregation logic fully tested
- [ ] Error handling paths tested

## Dependencies
**Must complete first**: None (standalone)
**Blocks**: Task 05 (CI/CD)

## Related Documentation
- **ARCHITECTURE.md**: Frontend section

---
**Estimated Time**: 3 hours
**Phase**: Foundation
