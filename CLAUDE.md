# HillsRun

## Overview
Trail-focused Garmin dashboard for athletes and coaches. Syncs health/sport data from Garmin Connect, visualizes trends, and supports multi-athlete coaching. Part of the HillsRun + RecettesApp ecosystem.

## Stack
- **Backend**: FastAPI (async) + asyncpg + Pydantic, self-hosted on UM880 (Coolify, internal-only)
- **Database**: Self-hosted PostgreSQL 16 on UM880 (Garmin tables via raw SQL, auth tables via Prisma)
- **Sync**: Python fetchers calling `garminconnect` lib, triggered on login + manual
- **Frontend**: Next.js 16 (App Router) + React 19 + TanStack Query + shadcn/ui + Tailwind CSS v4
- **Auth**: Better-Auth (email/password) + Prisma adapter
- **Charts**: Plotly.js (dynamic import, no SSR)
- **PWA**: Serwist service worker
- **Tunnel**: Cloudflare Tunnel for NAS SSH access
- **Tests**: Vitest (frontend), pytest (backend)

## Theme
- Shared with RecettesApp (dark mode by default via next-themes)
- Dark: orange primary (#FF8C00), cyan accent (#0891B2), navy background (#0F1419), slate cards (#1A2332)
- Light: deep blue primary (oklch), white background

## Project Structure
```
src/                          # Python backend
  api/
    main.py                   # FastAPI app, lifespan, DB init
    auth.py                   # API key validation (X-API-Key)
    dependencies.py           # Shared deps (get_db, date_range, pagination, coach access)
    schemas.py                # Pydantic response schemas + make_page()
    routers/                  # 10 routers (health, daily, body, metrics, activities, wellness, sync, auth_garmin, planned_workouts, coaching, user)
  database.py                 # asyncpg queries (upsert + query, multi-user, 1635 lines)
  garmin_client.py            # Garmin Connect API wrapper (retry + rate limiting)
  token_manager.py            # Fernet encryption for OAuth tokens in DB
  config.py                   # Dataclass config (DB, Garmin, Sync, Logging)
  sync_manager.py             # Orchestrates fetchers per category
  fetchers/                   # BaseFetcher + 5 subclasses (daily_health, activities, body_comp, advanced_metrics, wellness)

web/src/                      # Next.js frontend
  lib/                        # Auth, Prisma, garmin-api, garmin-user, coach-context, utils
  hooks/                      # 10 TanStack Query hooks (activities, metrics, trends, sync, coaching, vma, planned-workouts)
  components/                 # dashboard, activity, charts, calendar, settings, ui (shadcn)
  app/(dashboard)/            # Dashboard, calendar, trends, settings, activity/[id]
  app/(auth)/                 # Login, signup
  app/api/garmin/[...path]/   # Proxy to FastAPI (adds X-API-Key server-side)
  app/api/auth/[...all]/      # Better-Auth catch-all
  types/garmin.ts             # TypeScript types mirroring Pydantic schemas

specs/                        # Improvement task specs
sql/                          # DB migrations (applied manually)
config/config.yaml            # Sync config (categories, rate limits)
```

## API Endpoints
Base URL (internal): `http://api:8000` | Header: `X-API-Key`

| Group | Endpoints |
|---|---|
| Daily | `/api/v1/daily/{summary,sleep,stress,body-battery,heart-rate}` |
| Body | `/api/v1/body/composition` |
| Metrics | `/api/v1/metrics/{hrv,spo2,fitness,respiration,training-readiness}` |
| Activities | `/api/v1/activities`, `/{id}`, `/{id}/splits` |
| Wellness | `/api/v1/wellness/hydration` |
| Planned | `/api/v1/planned-workouts` (CRUD + `/import` + `/template`) |
| Auth | `/api/v1/auth/{connect,connect/mfa,status,disconnect}` |
| Sync | `/api/v1/sync/{status,trigger,jobs}` |
| Coaching | `/api/v1/coaching/{status,invite-codes,redeem,athletes,coaches,check-access}` |
| User | `/api/v1/user/vma` (GET + PATCH) |

## Development

### Frontend
```bash
cd web && pnpm dev            # Dev server
cd web && pnpm build          # Production build
cd web && pnpm lint           # ESLint
cd web && pnpm test           # Vitest
cd web && pnpm test:watch     # Vitest watch mode
```

### Backend
```bash
uv sync                       # Install Python deps
uv run python -c "from src.api.main import app"  # Verify imports
uv run pytest tests/          # Run tests
uv run ruff check src/        # Lint
uv run ruff format src/       # Format
```

### Deploy (UM880 / Coolify)
- Everything runs from `docker-compose.coolify.yml` on the UM880, managed by Coolify.
- Auto-deploy: `git push` to the deployed branch → Coolify rebuilds.
- Services: `web` (Next.js, public via Traefik + Cloudflare Tunnel → `hillsrun.com`),
  `api` (FastAPI, **internal-only** `http://api:8000`), `db` (Postgres 16, primary),
  `sync` (daily cron 06:00 Europe/Paris).
- Env vars set in the Coolify UI — full list and runbook in `docs/DEPLOY-UM880.md`.
- Frontend → backend: same-origin proxy `/api/garmin/*` forwards to `http://api:8000`
  (no public `api.hillsrun.com` anymore).

### Daily sync cron (UM880)
Handled by the `sync` service in the compose (hits the internal api):
```bash
0 6 * * * curl -s -X POST -H 'X-API-Key: <API_KEY>' http://api:8000/api/v1/sync/trigger
```

### Remote access
- **SSH**: `ssh um880`
- **App**: `https://hillsrun.com`
- **DB**: `ssh um880 "docker exec <db_container> psql -U garmin -d garmin_connect"`

## Conventions
- CRITICAL: `pnpm` for frontend, `uv` for Python (NEVER pip, NEVER npm)
- Language: French for exchanges, English for code and UI
- Google-style docstrings on all Python functions
- No polling hooks — use staleTime + invalidation after mutations
- Activity colors centralized in `lib/utils.ts` — never duplicate in components
- API key (`GARMIN_API_KEY`) is server-side only, never exposed to client
- Frontend calls `/api/garmin/*` proxy which forwards to FastAPI with auth headers
- Prisma schema has auth tables only — Garmin tables are NOT in Prisma (to avoid `db push` dropping them)

## Key Architecture Decisions
- ADR-001: Garmin tables NOT in Prisma (avoid db push dropping them)
- ADR-002: API proxy pattern (Next.js /api/garmin/* → FastAPI, injects X-API-Key server-side)
- ADR-003: Fernet encryption for OAuth tokens stored in DB
- ADR-004: TanStack Query with staleTime + invalidation (no polling)
- ADR-005: Plotly.js dynamic import (no SSR, chart-heavy app)
- ADR-006: Coach context via React Context + X-View-As-Athlete header
- ADR-007: Threaded sync jobs (prevent blocking FastAPI event loop)
- ADR-008: HillsRun theme shared with RecettesApp (dark mode, orange primary)
- ADR-009: ~~Backend on Railway~~ → Superseded: self-hosted on UM880 (Coolify), api internal-only
- ADR-010: ~~NAS PostgreSQL replica via Neon logical replication~~ → Superseded: primary Postgres self-hosted on UM880 (Neon retired)
- ADR-011: Single Coolify compose on UM880 (web public + api/db/sync internal); see docs/DEPLOY-UM880.md

## Documentation
- `PRD.md` — Product requirements (what and why)
- `ARCHITECTURE.md` — Technical architecture (how)
- `specs/` — Improvement task specs
- `docs/SCHEMA.md` — Database schema reference
- `docs/SETUP.md` — NAS deployment guide
- `docs/PLAN-API.md` — API implementation plan
- `docs/TROUBLESHOOTING.md` — Common issues

## Deployment

Full runbook: `docs/DEPLOY-UM880.md`. Pre-UM880 configs archived in `legacy/`.

### Infrastructure (UM880 / Coolify)
- **Single compose**: `docker-compose.coolify.yml` (auto-deploy on `git push`)
- **web**: Next.js, public via Traefik + Cloudflare Tunnel → `hillsrun.com`
- **api**: FastAPI, internal-only `http://api:8000` (`Dockerfile.api`)
- **db**: self-hosted Postgres 16 (primary, replaces Neon)
- **sync**: daily cron 06:00 Europe/Paris → internal api

### Environment Variables (Coolify UI)
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `API_KEY`, `GARMIN_TOKEN_KEY`,
`BETTER_AUTH_SECRET`, `BETTER_AUTH_URL`, `NEXT_PUBLIC_BETTER_AUTH_URL`, `LOG_LEVEL`, `TZ`.
`DATABASE_URL`, `GARMIN_API_URL`, `GARMIN_API_KEY` are derived in the compose.

## Known Issues
- `BETTER_AUTH_SECRET` has been rotated in Sprint 1 (was listed in specs/01-improvements/04-security-hardening.md)
- `score_feedback`, `hrv_status`, `chronic_load` in training_readiness are null from Garmin API
- ~~Scheduler sync has broken DB constraints~~ Fixed by sql/07_fix_sync_state_null_conflict.sql
- Legacy garmin user_id 67 has no better_auth link (old sync system data)
