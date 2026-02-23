# Task 06: RecettesApp Integration Preparation

## Context
RecettesApp and HillsRun share the same tech stack (Next.js, Better-Auth, PostgreSQL, shadcn/ui, Tailwind, same theme). The long-term goal is to integrate nutrition data from RecettesApp with training data from HillsRun. This task prepares the integration points.

## Scope
- Define API contract between RecettesApp and HillsRun
- Shared user identity (same Better-Auth instance or cross-auth)
- Daily calorie intake from RecettesApp → HillsRun dashboard
- Training load from HillsRun → RecettesApp calorie goal suggestions

## Implementation Details

### Design Decisions Needed
1. **Auth strategy**: Shared database? OAuth between apps? SSO?
2. **Data flow**: API calls? Shared database? Event-driven?
3. **UI integration**: Links between apps? Embedded widgets? Single app?

### Possible Approaches
- **Option A**: Shared PostgreSQL — both apps read/write same DB (simplest, tight coupling)
- **Option B**: API integration — RecettesApp exposes `/api/nutrition/daily` endpoint, HillsRun consumes it (loose coupling, more work)
- **Option C**: Merge into single Next.js app with route groups (most integrated, biggest refactor)

### Files to Create
- `docs/INTEGRATION.md` — Integration architecture document
- API contract specification (OpenAPI or markdown)

## Success Criteria
- [ ] Integration strategy documented and decided
- [ ] API contract defined (endpoints, schemas, auth)
- [ ] Shared user resolution mechanism designed
- [ ] Timeline for implementation estimated

## Dependencies
**Must complete first**: Tasks 01-05 (both apps stable and tested)
**Blocks**: Actual integration implementation (future phase)

## Related Documentation
- **RecettesApp PRD.md**: Future Hillsrun integration mentioned
- **RecettesApp ARCHITECTURE.md**: Stack alignment noted

---
**Estimated Time**: 2 hours (design only)
**Phase**: Planning
