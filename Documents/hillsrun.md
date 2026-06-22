---
tags:
  - projet
  - trail-running
  - fastapi
  - nextjs
  - hills-run
created: 2026-03-04
updated: 2026-04-21
status: paused
paused_since: 2026-04-21
reprise: pas de reprise dev — uniquement case study portfolio et article blog
type: projet
project: hillsrun
---

# HillsRun

## Description

Tableau de bord de suivi d'entraînement trail qui synchronise automatiquement les données athlètes depuis Garmin Connect vers PostgreSQL. Interface minimaliste pour les coureurs de trail : dénivelé, allure, fréquence cardiaque, indice de forme quotidien — sans encombrement superflu.

**URL** : https://hillsrun.com (frontend Vercel) · https://api.hillsrun.com (backend Railway)
**API** : https://api.hillsrun.com
**Repo** : privé (GitHub)

---

## Stack technique

### Backend (Python/FastAPI)
| Composant | Version | Rôle |
|-----------|---------|------|
| Python | 3.11+ | Runtime sync engine & API |
| FastAPI | ≥0.111 | REST API framework |
| asyncpg | ≥0.29 | Driver PostgreSQL asynchrone |
| garminconnect | ≥0.2.19 | Wrapper API Garmin Connect |
| garth | ≥0.4.46 | OAuth Garmin |
| cryptography (Fernet) | ≥42.0 | Chiffrement tokens OAuth |
| uv | Latest | Package manager Python |

### Frontend (Next.js)
| Composant | Version | Rôle |
|-----------|---------|------|
| Next.js | 16.1.6 | App Router, Turbopack, SSR |
| React | 19.2.3 | UI framework |
| TypeScript | ^5 | Type safety |
| Prisma | ^7.4 | ORM (tables auth uniquement) |
| TanStack Query | ^5.90 | Cache & data fetching |
| Better-Auth | ^1.4.18 | Auth email/password |
| shadcn/ui | Latest | Composants (Radix + Tailwind) |
| Tailwind CSS | ^4 | CSS utilitaire |
| Plotly.js | ^3.4 | Charts (client-side) |
| Serwist | ^9.5.6 | PWA service worker |
| pnpm | ^10 | Package manager (obligatoire) |

### Infrastructure
| Composant | Rôle |
|-----------|------|
| PostgreSQL 15+ (Neon) | Base de données principale |
| PostgreSQL (NAS) | Réplica en lecture seule |
| Railway | Déploiement backend (auto-deploy) |
| Vercel | Déploiement frontend (auto-deploy) |
| GitHub Actions | CI/CD (lint, build, tests) |
| Cloudflare Tunnel | Accès SSH distant au NAS |

---

## Architecture

```
Garmin Connect (OAuth + REST API)
        │
   FastAPI Backend (Railway)
   ├── GarminClient (rate limit, retry)
   ├── SyncManager (orchestrateur 5 fetchers)
   ├── REST API (11 routers, 40+ endpoints)
   └── Database (asyncpg pool)
        │
   PostgreSQL (Neon) — 30+ tables
        │ (réplication logique)
   PostgreSQL Replica (NAS, read-only)

   Next.js (Vercel)
   ├── API Proxy: /api/garmin/* → FastAPI
   ├── Auth: Better-Auth (email/password)
   ├── Charts: Plotly (client-side only)
   └── PWA: Serwist service worker
```

**Flux de données** : Client → `/api/garmin/*` (Next.js proxy, injecte X-API-Key server-side) → FastAPI → PostgreSQL

**Décisions clés** :
- Tables Garmin PAS dans Prisma (éviter `db push` accidentel en prod)
- Proxy API pattern (clé API jamais exposée côté client)
- Tokens OAuth chiffrés Fernet en base
- TanStack Query avec staleTime + invalidation (pas de polling)
- Plotly en dynamic import (pas de SSR, réduit le bundle)

---

## Fichiers clés

### Backend
| Fichier | Rôle |
|---------|------|
| `main.py` | CLI entry point (sync) |
| `src/api/main.py` | App FastAPI, init DB pool |
| `src/database.py` | 1635 lignes, 100+ requêtes asyncpg |
| `src/sync_manager.py` | Orchestration 5 fetchers |
| `src/garmin_client.py` | Client Garmin (retry + rate limit) |
| `src/token_manager.py` | Chiffrement Fernet tokens |
| `src/fetchers/` | 5 fetchers (daily, activities, body, metrics, wellness) |
| `src/training/` | 10 fichiers (plan d'entraînement, périodisation) |
| `sql/01_schema.sql` → `sql/10_*.sql` | 10 migrations SQL |

### Frontend
| Fichier | Rôle |
|---------|------|
| `web/src/app/(dashboard)/page.tsx` | Dashboard principal |
| `web/src/app/api/garmin/[...path]/route.ts` | API proxy |
| `web/src/lib/garmin-api.ts` | Fetch wrapper typé |
| `web/src/lib/auth.ts` | Config Better-Auth |
| `web/src/components/dashboard/` | Weekly summary, readiness |
| `web/src/components/charts/` | Visualisations Plotly |
| `web/prisma/schema.prisma` | Tables auth uniquement |

### Config & Deploy
| Fichier | Rôle |
|---------|------|
| `Dockerfile` / `Dockerfile.api` | Containers sync et API |
| `docker-compose.yml` | Dev local |
| `docker-compose.nas.yml` | Réplica NAS |
| `railway.toml` | Config Railway |
| `.github/workflows/ci.yml` | CI/CD pipeline |

---

## Commandes utiles

### Backend (Python/uv)
```bash
uv sync                          # Installer dépendances
uv run python main.py --full     # Sync complète (90 jours)
uv run python main.py --dry-run  # Preview sans écriture
uv run pytest tests/             # Tests
uv run ruff check src/           # Lint
uv run ruff format src/          # Format
```

### Frontend (pnpm uniquement)
```bash
cd web && pnpm dev               # Dev server (port 3000)
cd web && pnpm build             # Build production
cd web && pnpm lint              # ESLint
cd web && pnpm test              # Vitest
cd web && pnpm db:push           # Prisma db push (auth)
cd web && pnpm db:studio         # Prisma Studio
```

### Makefile
```bash
make setup        # Setup initial complet
make sync         # Sync incrémentale
make sync-full    # Sync 90 jours
make test         # Tests Python
make psql         # Console PostgreSQL
make status       # État sync en DB
make backup       # Backup database
```

### Docker
```bash
docker-compose up -d postgres
docker-compose up garmin-api     # API (port 8000)
```

### Deploy
- **Frontend** : `git push` → Vercel auto-deploy
- **Backend** : `git push` → Railway auto-deploy
- **NAS** : `docker compose -f docker-compose.nas.yml up -d`
- **Cron sync** : `0 5 * * *` → POST `/api/v1/sync/trigger`

---

## Liens
- [[RecettesApp]] — Thème partagé (dark mode, orange primary)
- [[LADTC]] — Écosystème commun
