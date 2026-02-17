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
- Sync: `/api/v1/sync/{status,trigger,jobs}` (trigger 404 bug non resolu - workaround: lancer sync container directement)

### Dashboard local
```bash
cd dashboard && API_BASE_URL=https://api.hillsrun.com API_KEY=ADD3F7ELUifY37coN6ttuRF4SAcgnsHPKGBdWDkHcio streamlit run app.py
```

## Current State (2026-02-17)

### Page Home — Implemented
- **Today's Metrics**: Readiness Score, Sleep Score, Body Battery, HRV (4 colonnes, pas de delta)
- **Weekly Summary**: Duration, distance + denivele par type d'activite, nombre d'activites, breakdown par type
- **Recent Activities**: 7 dernieres activites (icone, nom, duree, distance)
- **7-Day Trends**: 6 charts Plotly (Steps, Sleep Score, Resting HR, Body Battery, Weight, Training Readiness)

### Bugs fixes appliques
- HRV fetcher: donnees sous `data["hrvSummary"]` (pas a la racine) — fixe
- user_id mismatch: orphan user_id=1 supprime, dependency retry ajoutee
- floors_descended: schema `int` -> `float` (Garmin renvoie Decimal)
- Body Battery: fallback `charged_value` si `highest_value` null
- Weight chart: `timestamp` au lieu de `calendar_date` pour body_composition

### Known Issues
- Sync trigger 404: les routes sync/trigger et sync/jobs disparaissent apres rebuild API. Workaround: lancer le container sync directement.
- score_feedback, hrv_status, chronic_load dans training_readiness sont null cote Garmin

### Prochaines pages prevues
- Calendar
- Dashboard (PMC / Performance Management Chart)
- ATP (Annual Training Plan)

## Conventions
- Langue: francais pour les echanges, anglais pour le code
- Pas de CSS custom complexe pour l'instant
- Plotly avec axes, markers, day labels pour les trend charts
- Colonnes dynamiques: n'afficher que si la donnee existe
