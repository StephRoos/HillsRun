# Plan : API REST + HTTPS pour accès externe

## Contexte

Le projet HillsRun (sync Garmin Connect -> PostgreSQL) est déployé sur un NAS Ugreen et fonctionne en CLI. L'objectif est d'exposer les données via une API REST sécurisée accessible depuis l'extérieur, pour consultation directe et futur dashboard web.

**Infra actuelle** : NAS ARM64 (192.168.129.21), PostgreSQL sur port 15432, ports 80/443 occupés par le serveur web du NAS.

**Approche** : FastAPI (async, cohérent avec asyncpg existant) + auth par API key + reverse proxy NAS pour HTTPS.

---

## Fichiers à créer

```
src/api/
  __init__.py
  main.py              # App FastAPI, lifespan (connect/disconnect DB)
  auth.py              # Dependency API key (X-API-Key header)
  dependencies.py      # Dependencies partagées (db, user_id, date range, pagination)
  schemas.py           # Modèles Pydantic (réponses paginées + tous les types de données)
  routers/
    __init__.py
    health.py          # GET /health (non-authentifié, pour healthcheck Docker)
    daily.py           # GET /api/v1/daily/{summary,heart-rate,sleep,stress,body-battery}
    body.py            # GET /api/v1/body/composition
    metrics.py         # GET /api/v1/metrics/{hrv,spo2,fitness,respiration}
    activities.py      # GET /api/v1/activities, /activities/{id}, /activities/{id}/splits
    wellness.py        # GET /api/v1/wellness/hydration
    sync.py            # GET /api/v1/sync/status
Dockerfile.api         # Image séparée (python:3.11-slim + fastapi + uvicorn)
requirements-api.txt   # fastapi, uvicorn[standard]
```

## Fichiers à modifier

| Fichier | Modification |
|---------|-------------|
| `src/database.py` | Ajouter ~15 méthodes `query_*` read-only (SELECT + pagination) + `query_first_user()` |
| `docker-compose.yml` | Ajouter service `garmin-api` (port 8100:8000, depends_on postgres) |
| `.env` | Ajouter `API_KEY` et `API_PORT=8100` |

## Architecture des endpoints

Tous les endpoints sont **GET** (read-only), sous `/api/v1/`, authentifiés via header `X-API-Key` (sauf `/health`).

**Paramètres communs** : `start_date`, `end_date` (défaut: 30 derniers jours), `limit` (défaut 50, max 200), `offset`.

**Réponse paginée standard** :
```json
{ "data": [...], "pagination": { "total": 120, "limit": 50, "offset": 0, "has_more": true } }
```

| Route | Description |
|-------|------------|
| `GET /health` | Healthcheck (non-auth) |
| `GET /api/v1/daily/summary` | Résumés journaliers |
| `GET /api/v1/daily/heart-rate` | Samples FC (limit max 5000) |
| `GET /api/v1/daily/sleep` | Données de sommeil |
| `GET /api/v1/daily/stress` | Données de stress |
| `GET /api/v1/daily/body-battery` | Body battery |
| `GET /api/v1/body/composition` | Poids, IMC, masse grasse/musculaire |
| `GET /api/v1/metrics/hrv` | Variabilité cardiaque |
| `GET /api/v1/metrics/spo2` | Oxygène sanguin |
| `GET /api/v1/metrics/fitness` | VO2 Max, âge fitness |
| `GET /api/v1/metrics/respiration` | Fréquence respiratoire |
| `GET /api/v1/activities` | Liste activités (+ filtre `sport_type`, `activity_type`) |
| `GET /api/v1/activities/{id}` | Détail d'une activité |
| `GET /api/v1/activities/{id}/splits` | Splits/laps d'une activité |
| `GET /api/v1/wellness/hydration` | Hydratation |
| `GET /api/v1/sync/status` | État de la synchronisation |

## Méthodes query à ajouter dans `src/database.py`

Pattern commun pour chaque table :
```python
async def query_daily_summaries(self, user_id, start_date, end_date, limit=50, offset=0):
    total = await self.pool.fetchval("SELECT COUNT(*) FROM daily_summary WHERE user_id=$1 AND calendar_date BETWEEN $2 AND $3", ...)
    rows = await self.pool.fetch("SELECT * FROM daily_summary WHERE ... ORDER BY calendar_date DESC LIMIT $4 OFFSET $5", ...)
    return rows, total
```

Tables : `daily_summary`, `heart_rate_samples`, `sleep_data`, `stress_data`, `body_battery`, `body_composition`, `hrv_data`, `spo2_data`, `fitness_metrics`, `respiration_data`, `activities`, `activity_splits`, `hydration_data`, `sync_state`.

Plus : `query_first_user()` (résout le user_id unique au démarrage), `query_activity_by_id()`, `query_activity_splits()`.

## Docker : service `garmin-api`

```yaml
garmin-api:
  build:
    context: .
    dockerfile: Dockerfile.api
  container_name: garmin-api
  environment:
    POSTGRES_HOST: postgres
    POSTGRES_PORT: 5432
    POSTGRES_DB: ${POSTGRES_DB:-garmin_connect}
    POSTGRES_USER: ${POSTGRES_USER:-garmin}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    API_KEY: ${API_KEY}
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
  ports:
    - "${API_PORT:-8100}:8000"
  depends_on:
    postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
    interval: 30s
    timeout: 5s
    retries: 3
  restart: unless-stopped
  networks:
    - garmin-network
```

Pas de volume tokens/config nécessaire (read-only sur la DB).

## Point d'attention : `Config.validate()`

La méthode `validate()` dans `src/config.py:176` vérifie que le répertoire Garmin tokens existe. Le container API n'a pas de tokens. Solution : l'API utilise `Config.from_env()` **sans** appeler `validate()` — seul `config.database` est nécessaire.

## Reverse proxy NAS + HTTPS

Configuration manuelle dans l'interface du NAS :
- Source : `https://ton-domaine.com` (port 443)
- Destination : `http://localhost:8100`
- Le NAS gère le certificat SSL (Let's Encrypt)

## Ordre d'implémentation

1. ✅ **`requirements-api.txt`** — dépendances FastAPI/uvicorn
2. ✅ **`src/database.py`** — méthodes query ajoutées (query_* read-only + query_first_user)
3. ✅ **`src/api/`** — auth, dependencies, schemas, routers (health/daily/body/metrics/activities/wellness/sync), main
4. ✅ **`Dockerfile.api`** — image Docker pour l'API
5. ✅ **`docker-compose.yml` + `.env.example`** — service garmin-api ajouté
6. **Test local** — `docker-compose up -d garmin-api` + curl http://localhost:8100/health
7. **Deploy NAS** — `git pull` sur le NAS, `docker-compose build garmin-api`, `docker-compose up -d garmin-api`
8. **Configurer reverse proxy NAS** — Source HTTPS → `http://localhost:8100`
9. **Test externe** — `curl -H "X-API-Key: ..." https://ton-domaine.com/api/v1/sync/status`

## Vérification

1. `curl http://localhost:8100/health` → `{"status": "ok"}`
2. `curl -H "X-API-Key: ..." http://localhost:8100/api/v1/daily/summary` → données paginées
3. `curl http://localhost:8100/api/v1/daily/summary` (sans clé) → 401
4. `curl https://ton-domaine.com/api/v1/sync/status -H "X-API-Key: ..."` → état sync depuis l'extérieur
5. Swagger UI accessible à `https://ton-domaine.com/docs`
