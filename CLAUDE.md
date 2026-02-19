# HillsRun - Garmin Connect Dashboard

## Project Overview
Dashboard Streamlit pour visualiser les donnees de sante/sport synchronisees depuis Garmin Connect via une API REST (FastAPI + PostgreSQL).

## Architecture

### Stack
- **API**: FastAPI (async) + asyncpg + Pydantic, deployee sur Synology NAS (ARM64) dans Docker
- **Database**: PostgreSQL (container `garmin-postgres`)
- **Sync**: Fetchers Python qui appellent l'API Garmin Connect (lib `garminconnect`) et ecrivent en DB
- **Dashboard**: Streamlit + Plotly, consomme l'API REST
- **Tunnel**: Cloudflare Tunnel pour acces externe

### Fichiers cles
- `dashboard/app.py` — Point d'entree Streamlit (sidebar + navigation)
- `dashboard/home.py` — Page Home: metrics du jour, weekly summary, recent activities, 7-day trends
- `dashboard/utils.py` — Helpers: TE-to-TSS, format_duration, sport_icon
- `dashboard/api_client.py` — Client HTTP pour l'API REST
- `src/api/` — FastAPI app (routers: daily, metrics, body, activities, sync, auth_garmin, planned_workouts)
- `src/api/routers/auth_garmin.py` — Garmin connect/disconnect/status + MFA two-step flow
- `src/api/schemas.py` — Schemas Pydantic (Page, DailySummary, Activity, HrvData, TrainingReadiness, PlannedWorkout, etc.)
- `src/api/routers/planned_workouts.py` — CRUD + CSV import/template for planned workouts
- `src/database.py` — Queries asyncpg (upsert + query pour chaque type de donnee, multi-user with better_auth_user_id)
- `src/fetchers/` — Fetchers par categorie (daily_health, activities, body_composition, advanced_metrics, wellness)
- `src/garmin_client.py` — Wrapper Garmin Connect API avec retry + rate limiting
- `src/token_manager.py` — Fernet encryption/decryption pour Garmin OAuth tokens en DB

### NAS Deployment (192.168.129.21, user: Steph)
SSH alias: `ssh nas` (via `cloudflared access ssh --hostname ssh.hillsrun.com`, works remotely)
```bash
# Copy files (pas de git sur le NAS, fichiers owned by root)
# Methode rapide: docker cp dans le container running + restart
cat <local_file> | ssh nas "cat > /tmp/$(basename <local_file>) && docker cp /tmp/$(basename <local_file>) garmin-api:/app/<path>"
ssh nas "docker restart garmin-api"

# Rebuild complet API image (quand deps changent)
# Copy files to build dir via alpine (root-owned files)
cat <local_file> | ssh nas "cat > /tmp/$(basename <local_file>)"
ssh nas "docker run --rm -v /volume1/docker/garmin-sync/HillsRun:/build -v /tmp:/host-tmp alpine cp /host-tmp/$(basename <local_file>) /build/<path>"
ssh nas "cd /volume1/docker/garmin-sync/HillsRun && docker build -f Dockerfile.api -t garmin-api:arm64 ."

# Recreate API container
ssh nas "docker stop garmin-api && docker rm garmin-api && docker run -d --name garmin-api --network garmin-sync_garmin-network -p 8000:8000 -v /home/Steph/.garminconnect:/tokens:ro -v /volume1/docker/garmin-sync/HillsRun/config:/app/config:ro -e POSTGRES_HOST=garmin-postgres -e POSTGRES_PORT=5432 -e POSTGRES_DB=garmin_connect -e POSTGRES_USER=garmin -e POSTGRES_PASSWORD=\$(docker exec garmin-postgres printenv POSTGRES_PASSWORD) -e API_KEY=ADD3F7ELUifY37coN6ttuRF4SAcgnsHPKGBdWDkHcio -e GARMIN_TOKENS_DIR=/tokens -e CONFIG_PATH=/app/config/config.yaml -e GARMIN_TOKEN_KEY=\$(docker exec garmin-api printenv GARMIN_TOKEN_KEY) --restart unless-stopped garmin-api:arm64"

# Rebuild sync image
ssh nas "cd /volume1/docker/garmin-sync/HillsRun && docker build -f Dockerfile -t garmin-sync:arm64 ."

# Run sync manually
ssh nas "docker run --rm --network garmin-sync_garmin-network -v /home/Steph/.garminconnect:/tokens:ro -v /volume1/docker/garmin-sync/HillsRun/config:/app/config:ro -e POSTGRES_HOST=garmin-postgres -e POSTGRES_PORT=5432 -e POSTGRES_DB=garmin_connect -e POSTGRES_USER=garmin -e POSTGRES_PASSWORD=\$(docker exec garmin-postgres printenv POSTGRES_PASSWORD) -e GARMIN_TOKENS_DIR=/tokens garmin-sync:arm64 python main.py --full --days-back 90 --categories advanced_metrics"
```

### Docker containers on NAS
- `garmin-postgres` — PostgreSQL (DB: garmin_connect, user: garmin)
- `garmin-api` — FastAPI API (port 8000, network: garmin-sync_garmin-network)
- `garmin-sync-cloudflare-tunnel-1` — Cloudflare Tunnel (host network, routes to 127.0.0.1:8000)

### API endpoints
- `https://api.hillsrun.com` (via Cloudflare Tunnel)
- API Key header: `X-API-Key`
- Data endpoints: `/api/v1/daily/{summary,sleep,stress,body-battery,heart-rate}`, `/api/v1/body/composition`, `/api/v1/metrics/{hrv,spo2,fitness,respiration,training-readiness}`, `/api/v1/activities`, `/api/v1/planned-workouts`
- Auth: `/api/v1/auth/{connect,connect/mfa,status,disconnect}`
- Sync: `/api/v1/sync/{status,trigger,jobs}`

### Dashboard local
```bash
cd dashboard && API_BASE_URL=https://api.hillsrun.com API_KEY=ADD3F7ELUifY37coN6ttuRF4SAcgnsHPKGBdWDkHcio streamlit run app.py
```

## Web Frontend (Next.js)

### Stack
- **Framework**: Next.js 16 (App Router, Turbopack)
- **Auth**: Better-Auth (email/password) + Prisma adapter
- **ORM**: Prisma 7 with `@prisma/adapter-pg` (PostgreSQL driver adapter)
- **State**: TanStack Query (React Query) for server state
- **UI**: shadcn/ui + Tailwind CSS v4 + Lucide icons
- **Charts**: Plotly.js (dynamic import, SSR disabled) with trend lines + shared week ticks
- **Toasts**: Sonner (dark theme, bottom-right)
- **PWA**: manifest.json + icons (standalone, installable)

### Fichiers cles (web/src/)
- `lib/auth.ts` — Better-Auth server config (Prisma adapter, sync-on-login hook)
- `lib/auth-client.ts` — Better-Auth React client (useSession, signIn, signUp, signOut)
- `lib/prisma.ts` — Singleton Prisma client with PG adapter
- `lib/garmin-api.ts` — Client HTTP qui appelle le proxy `/api/garmin/*`
- `lib/garmin-db.ts` — Raw SQL queries pour les donnees Garmin via Prisma
- `types/garmin.ts` — Types TypeScript miroir des schemas Pydantic
- `hooks/use-activities.ts` — TanStack Query hooks (useActivities, useActivity, useActivitySplits)
- `hooks/use-metrics.ts` — Hooks metrics (useTrainingReadiness, useHrv, useFitnessMetrics, useSleep, useBodyComposition, useStress)
- `hooks/use-trends.ts` — Aggregation hebdo + filtrage par periode + WeekTick[] for shared x-axis
- `hooks/use-planned-workouts.ts` — TanStack Query hooks (CRUD + import for planned workouts)
- `components/charts/trend-charts.tsx` — 8 Plotly charts (weekly bars + daily scatter with trend lines + year annotations)
- `components/dashboard/activity-calendar.tsx` — Monthly calendar grid with colored activity dots + planned workout dashed dots
- `components/calendar/training-calendar.tsx` — Full-width monthly calendar with merged activities + planned workouts, side panel, create/edit
- `components/calendar/workout-dialog.tsx` — Create/edit/delete planned workout dialog (sport type, intensity, duration, distance)
- `components/calendar/import-dialog.tsx` — CSV import dialog with template download and preview
- `components/activity/similar-activities.tsx` — Similar activities by type and distance (±20%)
- `components/providers.tsx` — QueryClientProvider + Sonner Toaster
- `hooks/use-garmin-account.ts` — Hooks: useGarminAccount, useConnectGarmin (MFA-aware), useSubmitMfa, useDisconnectGarmin
- `lib/garmin-user.ts` — Server-side: resolve garmin user_id from Better-Auth session (cached 5min)
- `components/settings/garmin-connect-form.tsx` — Two-step form: credentials → MFA code input
- `app/api/garmin/[...path]/route.ts` — Proxy GET+POST+PATCH+DELETE vers FastAPI (ajoute X-API-Key + X-Garmin-User-Id server-side)
- `app/api/garmin/planned-workouts/import/route.ts` — Proxy multipart file upload for CSV import
- `app/api/garmin/auth/connect/route.ts` — Proxy connect (maxDuration=60 pour Garmin SSO)
- `app/api/garmin/auth/connect/mfa/route.ts` — Proxy MFA completion
- `app/api/garmin/auth/{disconnect,status}/route.ts` — Proxy disconnect/status
- `app/api/auth/[...all]/route.ts` — Better-Auth catch-all handler

### Pages
- `/` — Landing page
- `/login`, `/signup` — Auth pages
- `/dashboard` — Dashboard principal (weekly summary, readiness gauge, activity list/calendar toggle)
- `/activity/[id]` — Detail activite (metrics, splits, charts Plotly, PR/fav badges, device, similar activities)
- `/trends` — Tendances (8 charts: distance, D+, VO2max, HRV, training load, sleep, weight, stress) + trend lines + year axis + filtre 4w/3m/6m/1y
- `/calendar` — Training calendar: monthly view with planned workouts + completed activities, create/edit/delete, CSV import
- `/settings` — Profil (connected to Better-Auth updateUser), suppression compte (deleteUser)

### Prisma
- Schema: `web/prisma/schema.prisma` (auth tables only — User, Session, Account, Verification)
- Config: `web/prisma.config.ts` (Prisma 7 — defineConfig avec DATABASE_URL)
- Les tables Garmin NE SONT PAS dans le schema Prisma (pour eviter que `db push` les supprime)
- Auth tables creees via raw SQL (`prisma db execute`) pour ne pas toucher aux tables existantes

### Important
- **API Key security**: GARMIN_API_KEY est server-side only, jamais expose au client
- **Proxy pattern**: Le frontend appelle `/api/garmin/*` qui forward vers FastAPI avec la cle
- **DB access distant**: Via `cloudflared access tcp` (db.hillsrun.com -> localhost:15432)

## Deployment

### Frontend: Vercel (Hobby plan)
- Auto-deploy: Git integration a configurer (Settings → Git → Connect `StephRoos/HillsRun`, Root Directory = `web`)
- Deploy manuel: `npx vercel --prod --cwd web`
- `maxDuration = 60` sur les routes auth (Garmin SSO login est lent)

### Backend: NAS Docker (voir NAS Deployment ci-dessus)
- Fichiers owned by root → utiliser `docker cp` + `docker restart` pour update rapide

## Current State (2026-02-20)

### Implemented
- Landing page avec gradient hero, features section, "3 steps" section
- Auth (login/signup) avec Better-Auth + Prisma
- **Multi-user Garmin connect**: connect/disconnect via Settings, encrypted tokens in DB (Fernet)
- **Garmin MFA support**: two-step flow (credentials → MFA code), in-memory session store cote API, existing_user_id passthrough to prevent duplicate user creation on reconnect
- Dashboard: weekly summary, readiness SVG arc gauge, activity list avec filtres, calendar view toggle, "Connect your Garmin" prompt si non connecte
- Activity detail: metrics, secondary metrics, splits table, charts Plotly, PR/favorite badges, device name, description, similar activities
- Trends: 8 charts (2 weekly bars + 6 daily scatter with linear regression trend lines), shared WeekTick x-axis with year annotations, filtre 4w/3m/6m/1y
- Settings: profil, Garmin connect/disconnect/sync, delete account
- Toast notifications (sonner) for sync, rename, settings, errors
- Error boundary, 404 page, loading skeletons
- Mobile responsive (bottom nav + sidebar desktop)
- Sync-on-login: Better-Auth after hook triggers Garmin sync on sign-in (fire-and-forget, anti-flood via API 409)
- PWA: manifest.json, SVG icon, installable on mobile (standalone mode)
- sport_type fixed: fetcher falls back to activityType.typeKey when sport_type is uncategorized
- Per-user sync state and activity queries (user_id filtering)
- Vercel Git integration auto-deploy (Root Directory = `web`)
- **Training Calendar** (`/calendar`): full-width monthly calendar with planned workouts (dashed-outline dots) + completed activities (filled dots), side panel with day details, workout CRUD dialog (sport type, intensity, duration, distance), CSV import with template download
- Planned workouts: DB table `planned_workouts`, FastAPI CRUD + bulk CSV import, sport types (running, trail_running, cycling, swimming, strength_training, rest, stretching), intensities (easy, moderate, hard, race), `created_by_user_id` column for future coach role
- Dashboard calendar also shows planned workout dots (dashed outline)
- Navigation: Dashboard → Calendar → Trends → Settings (sidebar + mobile bottom nav)

### Known Issues
- Splits data vide en API (pas encore synce) — charts activite ne montrent rien
- BETTER_AUTH_SECRET a changer pour la production
- score_feedback, hrv_status, chronic_load dans training_readiness sont null cote Garmin
### Prochaines etapes
- Coach role (Phase 2): use `created_by_user_id` to allow coaches to create workouts for athletes
- Offline mode PWA (service worker)

## Conventions
- Langue: francais pour les echanges, anglais pour le code et l'UI
- Plotly avec axes, markers, day labels pour les trend charts
- Colonnes dynamiques: n'afficher que si la donnee existe
- pnpm comme package manager
