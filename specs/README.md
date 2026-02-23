# Implementation Tasks Overview

## Project Summary
**Product**: HillsRun — Trail-focused Garmin dashboard for athletes and coaches
**Tech Stack**: FastAPI (Python) + Next.js 16 + PostgreSQL + Better-Auth + TanStack Query + Plotly.js + shadcn/ui
**Current State**: Fully deployed (NAS backend + Vercel frontend). All core features implemented. Needs testing, CI/CD, security hardening, and RecettesApp integration prep.

## Task Execution Guidelines
- Read complete task before starting
- Check dependencies are met
- Follow existing patterns from ARCHITECTURE.md
- Backend: use `uv` for Python, `pytest` for tests, `ruff` for linting
- Frontend: use `pnpm`, `vitest` for tests, `eslint` for linting
- Validate against success criteria

## Improvement Tasks (specs/01-improvements/)

### Phase 1: Foundation (Testing)
- [ ] `01-backend-tests.md` — Python pytest suite (routers, database, fetchers, utils)
- [ ] `02-frontend-tests.md` — Vitest expansion (hooks, components, API wrapper)

### Phase 2: Core (Stability)
- [ ] `03-fix-scheduler.md` — Fix DB constraints, re-enable automated daily sync
- [ ] `04-security-hardening.md` — Rotate secrets, audit env vars, add .env.example

### Phase 3: Polish (Automation)
- [ ] `05-ci-cd.md` — GitHub Actions (lint + typecheck + test on PR)

### Phase 4: Planning (Integration)
- [ ] `06-recettes-integration.md` — Design RecettesApp ↔ HillsRun integration

## Dependency Map
```
01-backend-tests ──┐
                   ├──→ 05-ci-cd
02-frontend-tests ─┘

03-fix-scheduler (independent)
04-security (independent)

01-05 all ──→ 06-recettes-integration
```

## Feature Coverage (Existing)
- ✅ Dashboard: weekly summary, readiness, VMA, activity calendar
- ✅ Activity detail: metrics, splits, similar activities
- ✅ Calendar: TrainingPeaks-style, planned workouts, CSV import
- ✅ Trends: 8 Plotly charts with period selector
- ✅ Settings: profile, Garmin connect, coaching, preferences
- ✅ Garmin sync: incremental + full, auto on login
- ✅ Coaching: invite codes, multi-athlete viewing
- ✅ Auth: Better-Auth email/password
- ✅ PWA: offline support via Serwist
- ✅ Theme: shared with RecettesApp (dark mode, orange primary)

## Total Estimated Time: 12-15 hours
