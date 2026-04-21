# HillsRun

> **Statut : en prod, dev figé depuis 2026-04-21.**
> Frontend (Vercel) + backend (Railway) + Neon PostgreSQL + replica NAS opérationnels.
> Sync Garmin quotidien via cron NAS (05:00 UTC).
> **Aucune nouvelle feature prévue.** Seul usage futur : rédaction du case study portfolio.
> **Conditions de reprise** : pas de reprise dev — uniquement case study + éventuel article blog (« Comment j'ai connecté Garmin à mon propre dashboard »).
> Cadre dans la réduction de 9 à 3 projets actifs (roadmap v2 2026-04-21).

[![CI](https://github.com/stpmusic/HillsRun/actions/workflows/ci.yml/badge.svg)](https://github.com/stpmusic/HillsRun/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Trail-focused Garmin dashboard that shows only what matters: D+, pace, HR, and daily readiness. Built for trail runners who find Garmin Connect too noisy.

![Dashboard Screenshot](docs/screenshots/dashboard.png)
<!-- TODO: Add actual screenshots -->

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Garmin Connect  │────▶│  Python/FastAPI   │────▶│   PostgreSQL    │
│       API        │     │   Backend (NAS)   │     │  (Neon + NAS)   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │   Next.js 16     │◀─────────────┘
                        │   Dashboard      │
                        │  (Vercel/local)  │
                        └──────────────────┘
```

| Component | Stack |
|-----------|-------|
| **Backend** | Python 3.11+, FastAPI, asyncpg, uv |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind v4, shadcn/ui |
| **Auth** | Better-Auth (email/password) + Prisma adapter |
| **Charts** | Plotly.js (dynamic import, no SSR) |
| **Database** | PostgreSQL 15+ (Neon primary + NAS replica) |
| **Data fetching** | TanStack Query (client) + API routes (server) |
| **PWA** | Serwist service worker |
| **CI/CD** | GitHub Actions + Railway (backend) + Vercel (frontend) |

## Features

- **Comprehensive Garmin Sync**: Health, activities, body composition, HRV, SpO2, VO2max
- **Incremental & Full Sync**: Smart updates or full historical syncs
- **REST API**: Read-only FastAPI exposing all synced data, secured by API key
- **Trail Dashboard**: Weekly summary, readiness score, activity detail with charts
- **Trend Analysis**: Weekly trends (distance, D+, HR, HRV, VO2max)
- **Docker Deployment**: Easy deployment on any server or NAS
- **Automated Scheduling**: Built-in cron for daily syncs

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Garmin Connect account with valid OAuth tokens
- PostgreSQL 15+ (provided via Docker or Neon)
- Node.js 22+ & pnpm 10+ (for frontend)
- Python 3.11+ & uv (for backend dev)

### 1. Clone and Setup

```bash
git clone https://github.com/stpmusic/HillsRun.git
cd HillsRun

# Backend env
cp .env.example .env
# Edit .env with your values

# Frontend env
cp web/.env.example web/.env.local
# Edit web/.env.local with your values

# Config
cp config/config.yaml.example config/config.yaml
```

### 2. Backend — Garmin Sync + API

```bash
# Start PostgreSQL + init schema
docker-compose up -d postgres
./scripts/init_db.sh

# First sync (last 90 days)
docker-compose --profile sync run --rm garmin-sync --full

# Start API
docker-compose up -d garmin-api
```

### 3. Frontend — Dashboard

```bash
cd web
pnpm install
pnpm prisma generate
pnpm dev
```

Dashboard available at `http://localhost:3000`.

## Usage

### Sync Commands

```bash
# Dry run
docker-compose --profile sync run --rm garmin-sync --dry-run

# Sync specific categories
docker-compose --profile sync run --rm garmin-sync --categories daily_health activities

# Sync date range
docker-compose --profile sync run --rm garmin-sync --start-date 2024-01-01 --end-date 2024-01-31

# Full sync with custom history
docker-compose --profile sync run --rm garmin-sync --full --days-back 180
```

### Makefile

```bash
make help       # Show all commands
make build      # Build Docker images
make up         # Start all services
make down       # Stop all services
make test       # Run tests
make sync       # Run incremental sync
make backup     # Backup database
```

### API Endpoints

All `GET`, authenticated via `X-API-Key` header (except `/health`).
Swagger UI at `http://localhost:8100/docs`.

| Route | Description |
|-------|-------------|
| `/health` | Health check (no auth) |
| `/api/v1/daily/summary` | Daily health summary |
| `/api/v1/daily/heart-rate` | Intraday heart rate |
| `/api/v1/daily/sleep` | Sleep data |
| `/api/v1/daily/stress` | Stress levels |
| `/api/v1/daily/body-battery` | Body battery |
| `/api/v1/body/composition` | Weight, BMI, body fat |
| `/api/v1/metrics/hrv` | Heart rate variability |
| `/api/v1/metrics/spo2` | Blood oxygen |
| `/api/v1/metrics/fitness` | VO2 Max, fitness age |
| `/api/v1/activities` | Activities (filter: `sport_type`) |
| `/api/v1/activities/{id}` | Activity detail |

### Frontend Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/dashboard` | Weekly summary, readiness, activities |
| `/activity/:id` | Activity detail with metrics & charts |
| `/trends` | Weekly trends (distance, D+, HR, HRV) |
| `/settings` | Profile, units, account |

## Project Structure

```
HillsRun/
├── src/                    # Python backend (FastAPI)
│   ├── api/               # REST API (routers, schemas, auth)
│   ├── fetchers/          # Garmin data fetchers
│   ├── database.py        # asyncpg queries
│   ├── garmin_client.py   # Garmin API wrapper
│   ├── sync_manager.py    # Sync orchestration
│   └── token_manager.py   # OAuth token encryption
├── web/                    # Next.js frontend
│   ├── src/app/           # App Router pages & API routes
│   ├── src/components/    # React components (dashboard, charts, UI)
│   ├── src/hooks/         # TanStack Query hooks
│   └── prisma/            # Prisma schema (auth tables)
├── sql/                    # Database migrations
├── config/                 # YAML config (sync rules)
├── scripts/                # Setup, sync, backup scripts
├── tests/                  # pytest test suite
├── docs/                   # SCHEMA.md, SETUP.md, etc.
├── docker-compose.yml      # Local Docker setup
└── Makefile                # Dev commands
```

## Data Categories

| Category | Metrics |
|----------|---------|
| **Daily Health** | Steps, HR, stress, sleep, body battery, intensity minutes |
| **Activities** | Pace, HR, cadence, power, elevation, splits, training effects |
| **Body Composition** | Weight, BMI, body fat, muscle mass, metabolic age |
| **Advanced Metrics** | HRV, SpO2, VO2 Max, fitness age, respiration |
| **Wellness** | Hydration tracking |

## Development

### Backend

```bash
uv sync --dev
uv run ruff check src/       # Lint
uv run ruff format src/       # Format
uv run pytest tests/ -v       # Tests
```

### Frontend

```bash
cd web
pnpm install
pnpm lint                     # ESLint
pnpm build                    # Production build (includes typecheck)
pnpm test                     # Vitest
```

## Deployment

- **Backend**: Railway (auto-deploy from `main`) or NAS Docker
- **Frontend**: Vercel (auto-deploy from `main`)
- **Database**: Neon PostgreSQL (primary) + NAS read-only replica

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Backend: `uv run ruff check src/` and `uv run pytest tests/ -v` pass
- Frontend: `pnpm lint` and `pnpm test` pass
- No secrets in committed code

## License

MIT

## Acknowledgments

- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) — Garmin API wrapper
- [asyncpg](https://github.com/MagicStack/asyncpg) — PostgreSQL driver
- [FastAPI](https://fastapi.tiangolo.com/) — REST API framework
- [Next.js](https://nextjs.org/) — React framework
- [shadcn/ui](https://ui.shadcn.com/) — UI components
