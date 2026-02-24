# HillsRun

## Overview
Trail-focused Garmin dashboard for athletes and coaches. Syncs health/sport data from Garmin Connect, visualizes trends, and supports multi-athlete coaching. Part of the HillsRun + RecettesApp ecosystem.

## Stack
- **Backend**: FastAPI (async) + asyncpg + Pydantic, Docker on NAS (ARM64)
- **Database**: PostgreSQL (Garmin tables via raw SQL, auth tables via Prisma)
- **Sync**: Python fetchers calling `garminconnect` lib, triggered on login + manual
- **Frontend**: Next.js 16 (App Router) + React 19 + TanStack Query + shadcn/ui + Tailwind CSS v4
- **Auth**: Better-Auth (email/password) + Prisma adapter
- **Charts**: Plotly.js (dynamic import, no SSR)
- **PWA**: Serwist service worker
- **Tunnel**: Cloudflare Tunnel for remote access
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
Base URL: `https://api.hillsrun.com` | Header: `X-API-Key`

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

### Deploy frontend (Vercel)
- Auto-deploy: `git push` (Vercel Git integration, root = `web`)

### Deploy backend (NAS Docker)
```bash
# Quick update (hot-patch running container)
cat <file> | ssh nas "cat > /tmp/$(basename <file>) && docker cp /tmp/$(basename <file>) garmin-api:/app/<path>"
ssh nas "docker restart garmin-api"

# Full rebuild (when deps change)
ssh nas "cd /volume1/docker/garmin-sync/HillsRun && docker build -f Dockerfile.api -t garmin-api:arm64 ."
```

### Remote access
All via Cloudflare Tunnel — no VPN needed.
- **SSH**: `ssh nas`
- **API**: `https://api.hillsrun.com`
- **DB**: `cloudflared access tcp --hostname db.hillsrun.com --url localhost:15432`
- **Logs**: `ssh nas "docker logs garmin-api --tail 50"`

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

## Documentation
- `PRD.md` — Product requirements (what and why)
- `ARCHITECTURE.md` — Technical architecture (how)
- `specs/` — Improvement task specs
- `docs/SCHEMA.md` — Database schema reference
- `docs/SETUP.md` — NAS deployment guide
- `docs/PLAN-API.md` — API implementation plan
- `docs/TROUBLESHOOTING.md` — Common issues

## Deployment (Sprint 1)

### Database Migration
Applied: `sql/07_fix_sync_state_null_conflict.sql` (2026-02-24)
- Fixes ON CONFLICT constraint for NULL user_id in sync_state table
- Adds partial unique index for legacy global sync entries
- Enables proper upsert handling per-user vs. legacy sync

### Secret Rotation Procedure
New secrets generated and stored in `/tmp/sprint1_secrets_rotation.txt`:
1. **BETTER_AUTH_SECRET**: Session encryption for Better Auth (Vercel env var)
2. **API_KEY**: X-API-Key for backend authentication (Vercel + NAS env var)
3. **GARMIN_TOKEN_KEY**: Fernet symmetric key for OAuth token encryption (NAS env var only)

Deployment steps documented in `scripts/deploy-sprint1.sh` (manual guide).

### Daily Sync Cron Schedule
Configured to run at 06:00 Europe/Paris time (05:00 UTC):
```bash
0 5 * * * curl -X POST -H 'X-API-Key: <API_KEY>' https://api.hillsrun.com/api/v1/sync/trigger
```
Logs: `/var/log/hillsrun-sync.log` on NAS

### Verification Checklist
- [x] Backend tests: 119 passed
- [x] Frontend tests: 144 passed
- [x] Database migration applied
- [x] Environment variables updated (NAS + Vercel)
- [x] Docker container restarted
- [x] Cron job configured
- [ ] First scheduled sync executed (check next morning)
- [ ] API endpoints verified with new keys

## Known Issues
- `BETTER_AUTH_SECRET` has been rotated in Sprint 1 (was listed in specs/01-improvements/04-security-hardening.md)
- `score_feedback`, `hrv_status`, `chronic_load` in training_readiness are null from Garmin API
- ~~Scheduler sync has broken DB constraints~~ Fixed by sql/07_fix_sync_state_null_conflict.sql
- Legacy garmin user_id 67 has no better_auth link (old sync system data)
