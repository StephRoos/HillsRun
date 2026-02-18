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
- `src/api/` — FastAPI app (routers: daily, metrics, body, activities, sync)
- `src/api/schemas.py` — Schemas Pydantic (Page, DailySummary, Activity, HrvData, TrainingReadiness, etc.)
- `src/database.py` — Queries asyncpg (upsert + query pour chaque type de donnee)
- `src/fetchers/` — Fetchers par categorie (daily_health, activities, body_composition, advanced_metrics, wellness)
- `src/garmin_client.py` — Wrapper Garmin Connect API avec retry + rate limiting

### NAS Deployment (192.168.129.21, user: Steph)
```bash
# Copy files (pas de git sur le NAS)
scp -O <local_file> Steph@192.168.129.21:/volume1/docker/garmin-sync/HillsRun/<path>

# Rebuild API image
ssh Steph@192.168.129.21 "cd /volume1/docker/garmin-sync/HillsRun && docker build -f Dockerfile.api -t garmin-api:arm64 ."

# Recreate API container
ssh Steph@192.168.129.21 "docker stop garmin-api && docker rm garmin-api && docker run -d --name garmin-api --network garmin-sync_garmin-network -p 8000:8000 -v /home/Steph/.garminconnect:/tokens:ro -v /volume1/docker/garmin-sync/HillsRun/config:/app/config:ro -e POSTGRES_HOST=garmin-postgres -e POSTGRES_PORT=5432 -e POSTGRES_DB=garmin_connect -e POSTGRES_USER=garmin -e POSTGRES_PASSWORD=\$(docker exec garmin-postgres printenv POSTGRES_PASSWORD) -e API_KEY=ADD3F7ELUifY37coN6ttuRF4SAcgnsHPKGBdWDkHcio -e GARMIN_TOKENS_DIR=/tokens -e CONFIG_PATH=/app/config/config.yaml --restart unless-stopped garmin-api:arm64"

# Rebuild sync image
ssh Steph@192.168.129.21 "cd /volume1/docker/garmin-sync/HillsRun && docker build -f Dockerfile -t garmin-sync:arm64 ."

# Run sync manually
ssh Steph@192.168.129.21 "docker run --rm --network garmin-sync_garmin-network -v /home/Steph/.garminconnect:/tokens:ro -v /volume1/docker/garmin-sync/HillsRun/config:/app/config:ro -e POSTGRES_HOST=garmin-postgres -e POSTGRES_PORT=5432 -e POSTGRES_DB=garmin_connect -e POSTGRES_USER=garmin -e POSTGRES_PASSWORD=\$(docker exec garmin-postgres printenv POSTGRES_PASSWORD) -e GARMIN_TOKENS_DIR=/tokens garmin-sync:arm64 python main.py --full --days-back 90 --categories advanced_metrics"
```

### Docker containers on NAS
- `garmin-postgres` — PostgreSQL (DB: garmin_connect, user: garmin)
- `garmin-api` — FastAPI API (port 8000, network: garmin-sync_garmin-network)
- `garmin-sync-cloudflare-tunnel-1` — Cloudflare Tunnel (host network, routes to 127.0.0.1:8000)

### API endpoints
- `https://api.hillsrun.com` (via Cloudflare Tunnel)
- API Key header: `X-API-Key`
- Data endpoints: `/api/v1/daily/{summary,sleep,stress,body-battery,heart-rate}`, `/api/v1/body/composition`, `/api/v1/metrics/{hrv,spo2,fitness,respiration,training-readiness}`, `/api/v1/activities`
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
- **Charts**: Plotly.js (dynamic import, SSR disabled)

### Fichiers cles (web/src/)
- `lib/auth.ts` — Better-Auth server config (Prisma adapter, sync-on-login hook)
- `lib/auth-client.ts` — Better-Auth React client (useSession, signIn, signUp, signOut)
- `lib/prisma.ts` — Singleton Prisma client with PG adapter
- `lib/garmin-api.ts` — Client HTTP qui appelle le proxy `/api/garmin/*`
- `lib/garmin-db.ts` — Raw SQL queries pour les donnees Garmin via Prisma
- `types/garmin.ts` — Types TypeScript miroir des schemas Pydantic
- `hooks/use-activities.ts` — TanStack Query hooks (useActivities, useActivity, useActivitySplits)
- `hooks/use-metrics.ts` — Hooks metrics (useTrainingReadiness, useHrv, useFitnessMetrics, etc.)
- `hooks/use-trends.ts` — Aggregation hebdo + filtrage par periode
- `app/api/garmin/[...path]/route.ts` — Proxy GET+POST vers FastAPI (ajoute X-API-Key server-side)
- `app/api/auth/[...all]/route.ts` — Better-Auth catch-all handler

### Pages
- `/` — Landing page
- `/login`, `/signup` — Auth pages
- `/dashboard` — Dashboard principal (weekly summary, readiness, activity list)
- `/activity/[id]` — Detail activite (metrics, splits, charts Plotly)
- `/trends` — Tendances (6 charts, filtre 4w/3m/6m/1y)
- `/settings` — Profil, unites, suppression compte

### Prisma
- Schema: `web/prisma/schema.prisma` (auth tables only — User, Session, Account, Verification)
- Config: `web/prisma.config.ts` (Prisma 7 — defineConfig avec DATABASE_URL)
- Les tables Garmin NE SONT PAS dans le schema Prisma (pour eviter que `db push` les supprime)
- Auth tables creees via raw SQL (`prisma db execute`) pour ne pas toucher aux tables existantes

### Important
- **API Key security**: GARMIN_API_KEY est server-side only, jamais expose au client
- **Proxy pattern**: Le frontend appelle `/api/garmin/*` qui forward vers FastAPI avec la cle
- **DB access distant**: Via `cloudflared access tcp` (db.hillsrun.com -> localhost:15432)

## Current State (2026-02-18)

### Implemented
- Landing page avec hero, features, CTA
- Auth (login/signup) avec Better-Auth + Prisma
- Dashboard: weekly summary (D+, distance, temps, sorties), readiness card, activity list avec filtres
- Activity detail: metrics, secondary metrics, splits table, charts Plotly (elevation, pace, HR)
- Trends: 6 charts hebdo (distance, D+, duree, FC repos, HRV, VO2max) + filtre periode
- Settings: profil, unites, danger zone
- Error boundary, 404 page, loading skeletons
- Mobile responsive (bottom nav + sidebar desktop)
- Sync-on-login: Better-Auth after hook triggers Garmin sync on sign-in (fire-and-forget, anti-flood via API 409)

### Known Issues
- Splits data vide en API (pas encore synce) — charts activite ne montrent rien
- `sport_type` = 'uncategorized' pour toutes les activites (utiliser `activity_type` a la place)
- BETTER_AUTH_SECRET a changer pour la production
- score_feedback, hrv_status, chronic_load dans training_readiness sont null cote Garmin

### Prochaines etapes
- Ameliorer le design (couleurs, polish)
- Ajouter comparaison semaine precedente
- Calendar view
- PWA support

## Conventions
- Langue: francais pour les echanges et l'UI, anglais pour le code
- Plotly avec axes, markers, day labels pour les trend charts
- Colonnes dynamiques: n'afficher que si la donnee existe
- pnpm comme package manager
