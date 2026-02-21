# HillsRun

## Overview
Web app to visualize health/sport data synced from Garmin Connect. FastAPI + PostgreSQL backend on a UGREEN NAS, Next.js frontend on Vercel.

## Architecture

### Stack
- **Backend**: FastAPI (async) + asyncpg + Pydantic, Docker on NAS (ARM64)
- **Database**: PostgreSQL (container `garmin-postgres`)
- **Sync**: Python fetchers calling `garminconnect` lib, triggered on login + manual Sync button
- **Frontend**: Next.js 16 (App Router) on Vercel
- **Auth**: Better-Auth (email/password) + Prisma adapter
- **Tunnel**: Cloudflare Tunnel for remote access

### Project Structure
```
src/                          # Python backend
  api/
    main.py                   # FastAPI app, lifespan, DB init
    auth.py                   # API key validation (X-API-Key)
    dependencies.py           # Shared deps (get_db, date_range, pagination, coach access)
    schemas.py                # Pydantic response schemas + make_page()
    routers/
      health.py               # GET /health
      daily.py                # /api/v1/daily/{summary,sleep,stress,body-battery,heart-rate}
      body.py                 # /api/v1/body/composition
      metrics.py              # /api/v1/metrics/{hrv,spo2,fitness,respiration,training-readiness}
      activities.py           # /api/v1/activities (list, detail, update, splits)
      wellness.py             # /api/v1/wellness/hydration
      sync.py                 # /api/v1/sync/{status,trigger,jobs} — threaded async jobs
      auth_garmin.py          # /api/v1/auth/{connect,connect/mfa,status,disconnect}
      planned_workouts.py     # /api/v1/planned-workouts (CRUD, CSV import, template)
      coaching.py             # /api/v1/coaching/{status,invite-codes,redeem,athletes,coaches}
      user.py                 # /api/v1/user/vma (GET/PATCH — VMA estimated + manual)
  database.py                 # asyncpg queries (upsert + query, multi-user)
  garmin_client.py            # Garmin Connect API wrapper (retry + rate limiting)
  token_manager.py            # Fernet encryption for OAuth tokens in DB
  config.py                   # Dataclass config (DB, Garmin, Sync, Logging)
  sync_manager.py             # Orchestrates fetchers per category
  fetchers/
    base.py                   # BaseFetcher (date range, sync state, shared helpers)
    daily_health.py           # Steps, HR, sleep, stress, body battery
    activities.py             # Activities + splits sync + deletion detection
    body_comp.py              # Weight/body composition
    advanced_metrics.py       # HRV, SpO2, VO2 Max, respiration, training readiness
    wellness.py               # Hydration
  utils/
    logging_config.py         # setup_logging() with rotation
    retry.py                  # Tenacity retry + safe_api_call decorator

web/src/                      # Next.js frontend
  lib/
    auth.ts                   # Better-Auth server config (sync-on-login hook)
    auth-client.ts            # Better-Auth React client
    prisma.ts                 # Singleton Prisma client with PG adapter
    garmin-api.ts             # HTTP client for /api/garmin/* proxy
    garmin-user.ts            # Resolve garmin user_id (cached, deduplicated)
    utils.ts                  # Helpers + ACTIVITY_COLORS
    coach-context.tsx         # React context for coach viewing athlete data
    coach-access.ts           # Server-side coach access verification
  hooks/
    use-activities.ts         # useActivities, useActivity, useActivitySplits
    use-metrics.ts            # useTrainingReadiness, useHrv, useSleep, etc.
    use-trends.ts             # Weekly aggregation + WeekTick[] for shared x-axis
    use-planned-workouts.ts   # CRUD + import hooks
    use-garmin-account.ts     # useGarminAccount, useConnectGarmin (MFA-aware)
    use-coaching.ts           # useCoachingStatus, invite codes, athlete management
    use-sync.ts               # useSyncStatus, useTriggerSync (poll job until complete)
    use-vma.ts                # useVma, useUpdateVma (manual VMA override)
  components/
    charts/trend-charts.tsx   # 8 Plotly charts (bars + scatter + trend lines)
    calendar/                 # TrainingPeaks-style calendar, workout dialog, CSV import
    dashboard/                # Weekly summary, readiness gauge, VMA card, activity calendar, nav
    activity/                 # Detail page components (metrics, splits, similar)
    settings/                 # Garmin connect form, coaching section
    ui/                       # shadcn/ui components
  app/
    api/garmin/[...path]/     # Proxy to FastAPI (adds X-API-Key server-side)
    api/auth/[...all]/        # Better-Auth catch-all
    (dashboard)/              # Dashboard, calendar, trends, settings, activity detail
    (auth)/                   # Login, signup
  types/garmin.ts             # TypeScript types mirroring Pydantic schemas

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
| Activities | `/api/v1/activities`, `/api/v1/activities/{id}`, `/api/v1/activities/{id}/splits` |
| Wellness | `/api/v1/wellness/hydration` |
| Planned | `/api/v1/planned-workouts` (CRUD + `/import` + `/template`) |
| Auth | `/api/v1/auth/{connect,connect/mfa,status,disconnect}` |
| Sync | `/api/v1/sync/{status,trigger,jobs}` |
| Coaching | `/api/v1/coaching/{status,invite-codes,redeem,athletes,coaches,check-access}` |
| User | `/api/v1/user/vma` (GET + PATCH) |

## Development

### Local dev
```bash
# Frontend
cd web && pnpm dev

# Tests
cd web && pnpm test        # vitest
cd web && pnpm lint         # eslint
cd web && pnpm build        # production build

# Verify backend imports
python -c "from src.api.main import app"
```

### Deploy frontend (Vercel)
- Auto-deploy: `git push` (Vercel Git integration, root = `web`)
- Manual: `npx vercel --prod --cwd web`

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

### Docker containers (NAS)
- `garmin-postgres` — PostgreSQL (DB: garmin_connect, user: garmin)
- `garmin-api` — FastAPI (port 8000)
- `cloudflared-tunnel` — Routes to localhost:8000

## Conventions
- Language: French for exchanges, English for code and UI
- `pnpm` as package manager
- No polling hooks — use staleTime + invalidation after mutations
- Activity colors centralized in `lib/utils.ts` — never duplicate in components
- API key (`GARMIN_API_KEY`) is server-side only, never exposed to client
- Frontend calls `/api/garmin/*` proxy which forwards to FastAPI with auth headers
- Prisma schema has auth tables only — Garmin tables are NOT in Prisma (to avoid `db push` dropping them)
- Google-style docstrings on all Python functions

## Known Issues
- `BETTER_AUTH_SECRET` should be changed for production
- `score_feedback`, `hrv_status`, `chronic_load` in training_readiness are null from Garmin API
- Scheduler sync has broken DB constraints (`ON CONFLICT`) — needs migration before re-enabling
- Legacy garmin user_id 67 has no better_auth link (old sync system data)

## TODO
- Fix scheduler DB constraints and re-enable periodic sync
- Offline mode PWA (service worker)
