# HillsRun - Garmin Connect Dashboard

## Project Overview
Web app pour visualiser les donnees de sante/sport synchronisees depuis Garmin Connect via une API REST (FastAPI + PostgreSQL). Frontend Next.js deploye sur Vercel, backend sur NAS UGREEN.

## Architecture

### Stack
- **API**: FastAPI (async) + asyncpg + Pydantic, deployee sur NAS UGREEN (ARM64) dans Docker
- **Database**: PostgreSQL (container `garmin-postgres`)
- **Sync**: Fetchers Python qui appellent l'API Garmin Connect (lib `garminconnect`) et ecrivent en DB. Sync declenche uniquement au login (email sign-in/sign-up) et via bouton Sync manuel dans le dashboard
- **Frontend**: Next.js 16 (Vercel) — remplace l'ancien dashboard Streamlit (supprime)
- **Tunnel**: Cloudflare Tunnel pour acces externe

### Fichiers cles
- `src/api/` — FastAPI app (routers: daily, metrics, body, activities, sync, auth_garmin, planned_workouts, coaching)
- `src/api/routers/auth_garmin.py` — Garmin connect/disconnect/status + MFA two-step flow
- `src/api/schemas.py` — Schemas Pydantic (Page, DailySummary, Activity, HrvData, TrainingReadiness, PlannedWorkout, etc.)
- `src/api/routers/planned_workouts.py` — CRUD + CSV import/template for planned workouts
- `src/database.py` — Queries asyncpg (upsert + query pour chaque type de donnee, multi-user with better_auth_user_id)
- `src/fetchers/` — Fetchers par categorie (daily_health, activities, body_composition, advanced_metrics, wellness)
- `src/garmin_client.py` — Wrapper Garmin Connect API avec retry + rate limiting
- `src/token_manager.py` — Fernet encryption/decryption pour Garmin OAuth tokens en DB

### NAS Deployment (UGREEN, user: Steph)
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

# Run sync manually
ssh nas "docker run --rm --network garmin-sync_garmin-network -v /home/Steph/.garminconnect:/tokens:ro -v /volume1/docker/garmin-sync/HillsRun/config:/app/config:ro -e POSTGRES_HOST=garmin-postgres -e POSTGRES_PORT=5432 -e POSTGRES_DB=garmin_connect -e POSTGRES_USER=garmin -e POSTGRES_PASSWORD=\$(docker exec garmin-postgres printenv POSTGRES_PASSWORD) -e GARMIN_TOKENS_DIR=/tokens garmin-sync:arm64 python main.py --full --days-back 90 --categories advanced_metrics"
```

### Docker containers on NAS
- `garmin-postgres` — PostgreSQL (DB: garmin_connect, user: garmin)
- `garmin-api` — FastAPI API (port 8000, network: garmin-sync_garmin-network)
- `cloudflared-tunnel` — Cloudflare Tunnel (routes to 127.0.0.1:8000)

Containers supprimes:
- `garmin-dashboard-1` (Streamlit) — remplace par frontend Next.js sur Vercel
- `garmin-scheduler` (cron sync) — avait un bug de contrainte DB (`ON CONFLICT`), sync se fait maintenant via login et bouton manuel

### API endpoints
- `https://api.hillsrun.com` (via Cloudflare Tunnel)
- API Key header: `X-API-Key`
- Data endpoints: `/api/v1/daily/{summary,sleep,stress,body-battery,heart-rate}`, `/api/v1/body/composition`, `/api/v1/metrics/{hrv,spo2,fitness,respiration,training-readiness}`, `/api/v1/activities`, `/api/v1/planned-workouts`
- Auth: `/api/v1/auth/{connect,connect/mfa,status,disconnect}`
- Sync: `/api/v1/sync/{status,trigger,jobs}`
- Coaching: `/api/v1/coaching/{status,invite-codes,redeem,athletes,coaches}`

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
- `lib/auth.ts` — Better-Auth server config (Prisma adapter, sync-on-login hook — exact path match `/sign-in/email` only)
- `lib/auth-client.ts` — Better-Auth React client (useSession, signIn, signUp, signOut)
- `lib/prisma.ts` — Singleton Prisma client with PG adapter
- `lib/garmin-api.ts` — Client HTTP qui appelle le proxy `/api/garmin/*`
- `lib/garmin-user.ts` — Server-side: resolve garmin user_id from Better-Auth session (cached 5min for connected users, request deduplication to prevent thundering herd)
- `lib/garmin-db.ts` — Raw SQL queries pour les donnees Garmin via Prisma
- `lib/utils.ts` — Helpers (formatDuration, formatDistance, activityTypeLabel) + shared ACTIVITY_COLORS constant + getActivityColor()
- `lib/coach-context.tsx` — React context for coach viewing athlete data
- `types/garmin.ts` — Types TypeScript miroir des schemas Pydantic
- `hooks/use-activities.ts` — TanStack Query hooks (useActivities, useActivity, useActivitySplits)
- `hooks/use-metrics.ts` — Hooks metrics (useTrainingReadiness, useHrv, useFitnessMetrics, useSleep, useBodyComposition, useStress)
- `hooks/use-trends.ts` — Aggregation hebdo + filtrage par periode + WeekTick[] for shared x-axis
- `hooks/use-planned-workouts.ts` — TanStack Query hooks (CRUD + import for planned workouts)
- `hooks/use-garmin-account.ts` — Hooks: useGarminAccount (staleTime 60s), useConnectGarmin (MFA-aware), useSubmitMfa, useDisconnectGarmin
- `hooks/use-coaching.ts` — Hooks: useCoachingStatus (no polling), useGenerateInviteCode, useRedeemInviteCode, useRemoveAthlete, useRemoveCoach
- `hooks/use-sync.ts` — useSyncStatus (staleTime 60s, no polling), useTriggerSync (poll job until complete)
- `components/charts/trend-charts.tsx` — 8 Plotly charts (weekly bars + daily scatter with trend lines + year annotations)
- `components/dashboard/activity-calendar.tsx` — Monthly calendar with compact activity cards (colored left border) + planned workout cards (dashed border), max 2 visible + overflow
- `components/calendar/training-calendar.tsx` — Full-width monthly calendar with TrainingPeaks-style activity cards, click to navigate/edit, +N overflow, no side panel
- `components/calendar/workout-dialog.tsx` — Create/edit/delete planned workout dialog (sport type, intensity, duration, distance)
- `components/calendar/import-dialog.tsx` — CSV import dialog with template download and preview
- `components/activity/similar-activities.tsx` — Similar activities by type and distance (±20%)
- `components/providers.tsx` — QueryClientProvider + Sonner Toaster
- `components/settings/garmin-connect-form.tsx` — Two-step form: credentials → MFA code input
- `components/settings/coaching-section.tsx` — Coach invite codes, athlete list, redeem code
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
- `/calendar` — Training calendar: monthly view with TrainingPeaks-style cards, planned workouts + completed activities, create/edit/delete, CSV import
- `/settings` — Profil (connected to Better-Auth updateUser), Garmin connect/disconnect, coaching section, suppression compte

### Activity Colors
Shared in `lib/utils.ts` — running is blue (#3B82F6), trail_running is orange (#FF6B00) for clear distinction.

### Prisma
- Schema: `web/prisma/schema.prisma` (auth tables only — User, Session, Account, Verification)
- Config: `web/prisma.config.ts` (Prisma 7 — defineConfig avec DATABASE_URL)
- Les tables Garmin NE SONT PAS dans le schema Prisma (pour eviter que `db push` les supprime)
- Auth tables creees via raw SQL (`prisma db execute`) pour ne pas toucher aux tables existantes

### Important
- **API Key security**: GARMIN_API_KEY est server-side only, jamais expose au client
- **Proxy pattern**: Le frontend appelle `/api/garmin/*` qui forward vers FastAPI avec la cle
- **DB access distant**: Via `cloudflared access tcp` (db.hillsrun.com -> localhost:15432)
- **No polling**: Aucun refetchInterval dans les hooks — les donnees sont fetch au chargement et invalidees apres actions (sync, connect, etc.)
- **Garmin status cache**: Only cache `connected: true` results server-side (Vercel Lambda instances don't share memory, caching `false` would cause stale data after connecting)
- **Request deduplication**: `garmin-user.ts` deduplicates concurrent auth/status calls to prevent thundering herd on page load

## Deployment

### Frontend: Vercel (Hobby plan)
- Auto-deploy: Git integration (Settings → Git → Connect `StephRoos/HillsRun`, Root Directory = `web`)
- Deploy manuel: `npx vercel --prod --cwd web`
- `maxDuration = 60` sur les routes auth (Garmin SSO login est lent)
- Vercel CLI: connecte en tant que `stephaneroos-7891`

### Backend: NAS Docker (voir NAS Deployment ci-dessus)
- Fichiers owned by root → utiliser `docker cp` + `docker restart` pour update rapide

### Remote Access (fonctionne de n'importe ou)
Tout l'acces remote passe par Cloudflare Tunnel — pas de VPN ni port forwarding necessaire.
- **SSH NAS**: `ssh nas` (configure dans `~/.ssh/config`, ProxyCommand via `cloudflared access ssh --hostname ssh.hillsrun.com`, user: Steph)
- **API publique**: `https://api.hillsrun.com` (header `X-API-Key`)
- **DB distante**: `cloudflared access tcp --hostname db.hillsrun.com --url localhost:15432` puis connexion PostgreSQL sur `localhost:15432`
- **Frontend deploy**: `git push` → auto-deploy Vercel, ou `npx vercel --prod --cwd web`
- **Monitoring**: `ssh nas "docker logs garmin-api --tail 50"`, `ssh nas "docker ps"`
- **cloudflared**: installe dans `~/.local/bin/cloudflared`

### Workflow de dev remote
1. Code localement → `git push` → Vercel deploy automatique (frontend)
2. Modifier l'API → `docker cp` via `ssh nas` → `docker restart garmin-api`
3. Acceder a la DB → tunnel cloudflared vers `db.hillsrun.com`
4. Monitorer → `ssh nas "docker logs garmin-api --tail 50"`

## Current State (2026-02-21)

### Implemented
- Landing page avec gradient hero, features section, "3 steps" section
- Auth (login/signup) avec Better-Auth + Prisma
- **Multi-user Garmin connect**: connect/disconnect via Settings, encrypted tokens in DB (Fernet)
- **Garmin MFA support**: two-step flow (credentials → MFA code), in-memory session store cote API, existing_user_id passthrough to prevent duplicate user creation on reconnect
- Dashboard: weekly summary, readiness SVG arc gauge, activity list avec filtres, calendar view toggle with TrainingPeaks-style cards, "Connect your Garmin" prompt si non connecte
- Activity detail: metrics, secondary metrics, splits table, charts Plotly, PR/favorite badges, device name, description, similar activities
- Trends: 8 charts (2 weekly bars + 6 daily scatter with linear regression trend lines), shared WeekTick x-axis with year annotations, filtre 4w/3m/6m/1y
- Settings: profil, Garmin connect/disconnect/sync, coaching section, delete account
- Toast notifications (sonner) for sync, rename, settings, errors
- Error boundaries per route (dashboard, trends, calendar) + isError handling in components
- Mobile responsive (bottom nav + sidebar desktop), safe-area-inset-bottom on mobile nav
- Sync-on-login: Better-Auth after hook triggers Garmin sync on email sign-in only (exact path match, not session revalidation)
- PWA: manifest.json, SVG + PNG icons (192/512), installable on mobile (standalone mode), apple-touch-icon
- sport_type fixed: fetcher falls back to activityType.typeKey when sport_type is uncategorized
- Per-user sync state and activity queries (user_id filtering)
- Vercel Git integration auto-deploy (Root Directory = `web`)
- **Training Calendar** (`/calendar`): TrainingPeaks-style monthly calendar with activity cards (colored left border, name + metrics), planned workout cards (dashed border), click activity → detail page, click planned → edit dialog, +N overflow, CSV import
- **Dashboard Calendar**: compact activity cards (colored bar + name), max 2 visible + overflow, selected day detail panel
- Planned workouts: DB table `planned_workouts`, FastAPI CRUD + bulk CSV import (max 1 MB), sport types (running, trail_running, cycling, swimming, strength_training, rest, stretching), intensities (easy, moderate, hard, race), `created_by_user_id` column for coach role
- Navigation: Dashboard → Calendar → Trends → Settings (sidebar + mobile bottom nav)
- Coaching: invite codes, athlete list, view athlete data, redeem invite code, mobile athlete switcher (Select in bottom nav), "View" button in settings, "for [athlete]" badge in workout dialog
- **Activity splits sync**: fetcher calls `get_activity_splits()` per activity and stores via `upsert_activity_splits()` (non-blocking, try/except)
- **DB migration documented**: `sql/06_sync_state_per_user.sql` (per-user sync_state), `sql/01_schema.sql` updated to reflect live DB
- **Security**: `hmac.compare_digest` for API key comparison, `GARMIN_TOKEN_KEY` validated at startup (Fernet key check), ReactQueryDevtools excluded from prod bundle
- **API logging**: `setup_logging()` called in FastAPI lifespan
- **Thread safety**: `threading.Lock()` on `_jobs` in sync router
- **Proxy error forwarding**: upstream FastAPI error `detail` forwarded to frontend (instead of generic "Garmin API error: {status}")
- **Env var rename**: `NEXT_PUBLIC_GARMIN_API_URL` → `GARMIN_API_URL` (server-side only, never exposed to client)
- **Build optimization**: `optimizePackageImports: ["lucide-react"]` in next.config.ts
- A11y: skip-to-main-content link, `role="img"` + `aria-label` on SVG gauge, keyboard navigation on calendar cells, aria-labels on icon buttons
- Utility tests: `pnpm test` runs vitest (formatDuration, formatDistance, formatPace, formatElevation, getActivityColor, activityTypeLabel)
- Streamlit dashboard removed (replaced by Next.js frontend on Vercel)
- Scheduler container removed (had ON CONFLICT DB bug, sync via login + manual button only)

### Known Issues
- BETTER_AUTH_SECRET a changer pour la production
- score_feedback, hrv_status, chronic_load dans training_readiness sont null cote Garmin
- Scheduler sync broken: `there is no unique or exclusion constraint matching the ON CONFLICT specification` — needs DB migration to fix unique constraints before re-enabling
- Garmin user_id 67 (`Roos Stephane`) has no better_auth_user_id link and no tokens — legacy entry from old sync system, historical data is under this user_id

### Prochaines etapes
- Fix scheduler DB constraints and re-enable periodic sync
- Offline mode PWA (service worker)

## Conventions
- Langue: francais pour les echanges, anglais pour le code et l'UI
- Plotly avec axes, markers, day labels pour les trend charts
- Colonnes dynamiques: n'afficher que si la donnee existe
- pnpm comme package manager
- No polling hooks — use staleTime + invalidation after mutations
- Activity colors centralized in `lib/utils.ts` — never duplicate in components
