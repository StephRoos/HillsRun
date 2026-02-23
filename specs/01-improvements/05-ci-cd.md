# Task 05: CI/CD Pipeline (GitHub Actions)

## Context
HillsRun has no automated CI/CD. No linting, type checking, or testing runs on pull requests. Frontend deploys via Vercel git integration (auto), backend deploys manually via Docker. Adding GitHub Actions for quality gates.

## Scope
- GitHub Actions workflow for pull requests (lint + typecheck + test)
- Separate jobs for frontend and backend
- Vercel preview deploys already work via git integration

## Implementation Details

### Files to Create
- `.github/workflows/ci.yml` — Main CI pipeline

### Workflow Structure
```yaml
on: [push, pull_request]
jobs:
  frontend:
    - pnpm install
    - pnpm lint
    - pnpm build (includes typecheck)
    - pnpm test
  backend:
    - uv sync
    - ruff check src/
    - ruff format --check src/
    - python -c "from src.api.main import app" (import check)
    - pytest tests/ (after Task 01)
```

### Key Functionality
- Cache pnpm store and uv cache for speed
- Run frontend and backend jobs in parallel
- Fail fast on lint/type errors
- PostgreSQL service container for backend integration tests (optional)

### Technologies Used
- GitHub Actions
- pnpm (frontend)
- uv (Python)
- ruff (Python linting/formatting)

## Success Criteria
- [ ] CI runs on every push to main and on PRs
- [ ] Frontend: lint + build + test pass
- [ ] Backend: ruff + import check + pytest pass
- [ ] Pipeline completes in <5 minutes
- [ ] Failed checks block PR merge

## Dependencies
**Must complete first**: Task 01 (backend tests), Task 02 (frontend tests)
**Blocks**: None

## Related Documentation
- **ARCHITECTURE.md**: Deployment section

---
**Estimated Time**: 1.5 hours
**Phase**: Polish
