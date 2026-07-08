# HANDOFF — HillsRun

> AI/human handoff document. Goal: resume work with zero prior context.
> Last audit: 2026-07-07. Complements (does not replace) `README.md`, `CLAUDE.md`,
> `ARCHITECTURE.md`, `PRD.md` and `docs/DEPLOY-UM880.md`.
>
> **Read `CLAUDE.md` first** — it is the most current concise reference.
> **`README.md`'s status header is STALE** (see Pitfalls below).

## 1. What this is

HillsRun is Stéphane's main personal project: a trail/road running dashboard that
syncs Garmin Connect data (health, activities, HRV, VO2max, body composition) into
PostgreSQL and visualizes what matters to trail runners: elevation gain (D+), pace,
HR, daily readiness. On top of the dashboard it has a **training plan engine**
(trail + road marathon) and an **adaptive coach** (readiness-driven weekly plan
reconciliation, propose/apply model).

- Users: Stéphane (primary athlete), plus multi-athlete coaching support
  (invite codes, coach view).
- Live product: **https://hillsrun.com** (verified up on 2026-07-07,
  `/api/health` → `{"status":"ok","backend_reachable":true}`).
- Ecosystem fit: flagship of the personal Next.js ecosystem; shares theme and a
  nutrition endpoint with RecettesApp (planned); hosted on the UM880 homelab
  behind Cloudflare Tunnel like the other Anthemion/homelab apps (ladtc, portfolio).
- Concrete personal driver: **road marathon in Bruges, 2026-10-12** — the app
  generated and hosts his actual marathon plan (`specs/mon-plan-marathon.md`,
  seeded via PR #10).

## 2. Current state (2026-07-07)

**Maturity: production.** Deployed, used daily (cron sync at 06:00), CI green enough.

- Last commit: `33c5760` (2026-06-29) "fix(deploy): publish web on loopback :3001
  for Cloudflare Tunnel" — that commit put hillsrun.com back online after the
  homelab moved off Coolify's Traefik to direct Cloudflare Tunnel routing.
- Working tree: clean except this untracked `HANDOFF.md`; `main` in sync with
  `origin/main`.
- June 2026 sprint (largely done via the Ralph autonomous loop, `.vibe/ralph-tasks/`):
  - **Road marathon plan engine** (spec `specs/02-road-marathon-adaptation.md`,
    Lots 1–7): pace calculator (VMA + VDOT fallback), MPR sessions, road long-run
    variants, week builder — all merged (PRs #3–#10).
  - **Adaptive coach** (spec `specs/03-adaptive-coach.md`, D1–D4): readiness
    agent, weekly reconciliation, `propose-adjustment` / `apply` endpoints
    (no plan mutation without explicit apply). Merged.
  - Bruges marathon plan seeded as `planned_workouts` (PR #10).
  - garminconnect 0.3.x token/MFA migration (`f4dd3e3`, PR #5) + rate-limiter
    fix (PR #4). NOTE: `uv.lock` was not re-locked — see the version-skew
    pitfall in §7.
- Backend test suite: 961 tests collected (verified 2026-07-07); last full run
  940 passed with **2 known pre-existing failures** (CORS `env_override` + MFA
  cleanup — see `.vibe/ralph-tasks/progress.txt`).
  Smoke check 2026-07-07: `pytest tests/test_health.py tests/test_config.py` → 31 passed.
- Half-done / open: frontend test expansion (~20% of spec
  `specs/01-improvements/02-frontend-tests.md`), RecettesApp integration
  (design done, shared auth not started), adaptive-coach UI polish, README refresh.
- All 4 local branches (`feat/road-marathon-engine`, `feat/road-marathon-plan-ui`,
  `fix/lint-no-explicit-any`, `migrate/um880`) are merged into main — safe to delete.

## 3. Architecture & stack

Full details: `ARCHITECTURE.md` (long, partially pre-UM880) and `CLAUDE.md` (current).

```
Garmin Connect ──> FastAPI backend (src/)  ──> PostgreSQL 16 (UM880, primary)
                        ▲    internal-only http://api:8000
Next.js 16 web (web/) ──┘  via same-origin proxy /api/garmin/* (injects X-API-Key)
Cloudflare Tunnel: hillsrun.com → http://localhost:3001 (web published on loopback)
sync service: cron 06:00 Europe/Paris → POST /api/v1/sync/trigger
```

- **Backend** (`src/`, ~13.5k lines Python 3.11+): FastAPI + asyncpg + Pydantic.
  - `src/api/routers/` — 14 routers (daily, body, metrics, activities, wellness,
    sync, auth_garmin, planned_workouts, training_plans, training, coaching, user,
    nutrition, health).
  - `src/training/` — plan engine: `plan_generator.py`, `week_builder.py`,
    `session_catalog.py`, `pace_calculator.py`, `long_run.py`, `race_classifier.py`,
    `periodization.py`, `load_calculator.py`, `hr_zones.py`, `adaptive/` (coach).
  - `src/garmin_client.py` (retry + rate limiting), `src/sync_manager.py`,
    `src/token_manager.py` (Fernet-encrypted OAuth tokens in DB),
    `src/database.py` (raw asyncpg queries, multi-user).
- **Frontend** (`web/`, ~24k lines TS): Next.js 16 App Router, React 19,
  TanStack Query, shadcn/ui, Tailwind v4, Plotly.js (dynamic import, no SSR),
  Better-Auth + Prisma (auth tables ONLY), Serwist PWA.
- **DB**: raw SQL migrations in `sql/01…14` (applied manually, no tracking table).
  Prisma manages ONLY auth tables (ADR-001: Garmin tables kept out of Prisma so
  `db push` cannot drop them).
- **Deploy**: `docker-compose.coolify.yml` (4 services: db, api, web, sync) on the
  UM880 (192.168.129.10) via Coolify; auto-deploy on push to `main` through the
  GitHub App `hillsrun-coolify` (App ID 4006693). Pre-UM880 configs archived in
  `legacy/` (Vercel/Railway/Neon/NAS — all retired).
- Key ADRs: `CLAUDE.md` §Key Architecture Decisions (ADR-001…012).

## 4. How to run

### Backend (Python — always `uv`, never pip)
```bash
uv sync
uv run pytest tests/ -q          # 961 tests, 2 known failures (CORS, MFA cleanup)
uv run ruff check src/ && uv run ruff format src/
uv run python -c "from src.api.main import app"   # import smoke test
uv run uvicorn src.api.main:app --reload --port 8000   # run the API locally
```
Tests mock all external services — no DB or Garmin account needed for the suite.
Running the API locally DOES need a Postgres (see "Local full stack" below).

### Frontend (Node — always `pnpm`, never npm)
```bash
cd web
pnpm install                     # runs prisma generate via postinstall
pnpm dev                         # http://localhost:3000
pnpm lint && pnpm test && pnpm build
```

### Local full stack
`docker-compose.yml` (local) + `./scripts/init_db.sh`; see README Quick Start.
`make help` lists Makefile shortcuts (build/up/down/test/sync/backup).

### Production (UM880 / Coolify)
- Push to `main` → Coolify rebuilds automatically. Runbook: `docs/DEPLOY-UM880.md`.
- Coolify UI: https://coolify.anthemion.dev (Cloudflare Tunnel →
  `localhost:8000` on the UM880; env var values live there).
- Access: `ssh um880` (host alias in `~/.ssh/config`, target 192.168.129.10);
  app at https://hillsrun.com; DB via
  `ssh um880 "docker exec <db_container> psql -U garmin -d garmin_connect"`.
- Web is published on `127.0.0.1:3001` (3000 is taken by ladtc); Cloudflare
  Tunnel forwards hillsrun.com there. api/db/sync have NO published ports.

## 5. Dependencies & credentials

Env var NAMES (values live in the Coolify UI, never in git):
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `API_KEY`,
`GARMIN_TOKEN_KEY` (Fernet), `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL`,
`NEXT_PUBLIC_BETTER_AUTH_URL` (build arg — inlined at image build),
`LOG_LEVEL`, `TZ`. Derived in the compose: `DATABASE_URL`, `GARMIN_API_URL`,
`GARMIN_API_KEY` (= `API_KEY`). Local dev: `.env.example` and `web/.env.local`
(see `.env.example` bottom section).

External services: Garmin Connect (via `garminconnect` + `garth`; user OAuth
tokens Fernet-encrypted in DB — see the version-skew pitfall in §7), Cloudflare
(DNS + Tunnel), GitHub
(`StephRoos/HillsRun`, private) + GitHub App `hillsrun-coolify`, Coolify on UM880.
No paid cloud left (Vercel/Railway/Neon retired June 2026).

## 6. Open work (ordered)

1. **Marathon prep is the live use case (race 2026-10-12)** — dogfood the plan +
   adaptive coach weekly; fix friction as it appears. The weekly reconciliation
   flow (`propose-adjustment` → `apply`) is backend-complete; verify/finish its UI.
2. **Refresh `README.md`** — the status header ("frozen, Vercel/Railway/Neon") and
   the CI badge URL (`stpmusic/HillsRun` instead of `StephRoos/HillsRun`) are wrong;
   screenshots TODO at line 18.
3. **Fix the 2 known failing backend tests** (CORS env_override, MFA cleanup).
4. **Frontend tests** — expand per `specs/01-improvements/02-frontend-tests.md`
   (~20% done; 27 vitest files exist but hooks/API-wrapper coverage is thin).
5. **Migration tracking** — 14 manual SQL files, no tracking table; schema drift
   already bit once (Daily 2026-06-09). Add a tracking table or idempotent runner.
6. **RecettesApp integration** (`specs/01-improvements/06-recettes-integration.md`)
   — nutrition endpoint exists, shared auth to design/build. Blocked on RecettesApp
   itself resuming.
7. **Portfolio case study + blog article** ("How I connected Garmin to my own
   dashboard") — planned since April, high career-change value, never started.
8. Housekeeping: delete 4 merged local branches (and ~10 stale merged remote
   branches on origin); re-lock `garminconnect` in `uv.lock` (§7); clear root cruft
   (`ralph-run.log`, `telegram-watch.log`, `.coverage` — gitignored but noisy);
   `~/Projects/hills-run-telegram-watch.sh` is a leftover Ralph watcher.

Known data quirks (`CLAUDE.md` §Known Issues): `score_feedback`, `hrv_status`,
`chronic_load` come back null from Garmin; legacy garmin user_id 67 has no
better_auth link.

## 7. Pitfalls & gotchas

- **README header is stale.** It describes the April 2026 state ("dev frozen,
  Vercel + Railway + Neon, cron on NAS"). Reality since June 2026: everything
  self-hosted on UM880/Coolify, active development, Neon/Railway/Vercel retired.
  Trust `CLAUDE.md` and `docs/DEPLOY-UM880.md`.
- **Never run `prisma db push` carelessly** — Prisma only knows the auth tables;
  Garmin tables are raw SQL by design (ADR-001).
- **SQL migrations are manual and untracked.** `sql/12–14` were explicitly
  verified applied on UM880 prod (Daily 2026-06-09, likely via the Neon
  `pg_restore`); `sql/11` (road_marathon) is implied applied since the plan
  wizard works in prod, but was never individually verified. Before writing
  migration 15+, check what's actually in prod
  (`ssh um880 "docker exec <db_container> psql -U garmin -d garmin_connect -c '\dt'"`).
- **Routing model changed June 2026**: coolify-proxy (Traefik) is intentionally
  stopped on the UM880. Apps are published on loopback host ports + Cloudflare
  Tunnel per-domain. HillsRun = port 3001. When adding tunnel hostnames, service
  Type must be `HTTP` (an `HTTPS` type causes
  `tls: first record does not look like a TLS handshake`).
- **`NEXT_PUBLIC_*` vars are build args** — changing them in Coolify requires a
  rebuild, not a restart.
- **`API_KEY` and `GARMIN_API_KEY` must be identical** (compose maps one to the
  other); the sync cron and web proxy both authenticate with it.
- **`garminconnect` version skew (local vs prod)**: the code was migrated to the
  garminconnect **0.3.x** token/MFA API (commit `f4dd3e3`), but `uv.lock` still
  resolves **0.2.38** and `pyproject.toml`/`requirements-api.txt` only pin
  `>=0.2.19`. Prod Docker images pip-install the latest at build time (0.3.x),
  so prod works; a local `uv sync` env may NOT for real Garmin auth flows
  (tests are unaffected — everything is mocked). Re-lock (`uv lock --upgrade-package
  garminconnect`) before debugging Garmin auth locally.
- **Two similarly named routers**: `training_plans.py` (plans CRUD/generation)
  vs `training.py` — check both before adding endpoints.
- The `.vibe/` directory is Ralph autonomous-loop state (tasks.json, progress.txt)
  — valuable as a change log of the June sprint, not app code.
- Tests mock all external services; CI (`.github/workflows/ci.yml`) uses fake env
  vars. No DB needed to run the suite.

## 8. Pointers

- In-repo docs: `CLAUDE.md` (current reference), `PRD.md`, `ARCHITECTURE.md`
  (long-form, partly pre-UM880), `docs/DEPLOY-UM880.md` (deploy runbook),
  `docs/SCHEMA.md`, `docs/TROUBLESHOOTING.md`, `docs/PLAN-API.md`,
  `docs/PERFORMANCE.md` (`docs/SETUP.md` = legacy NAS guide, pre-UM880),
  `specs/` (feature specs), `RUN.md` (June Ralph-loop runbook — historical,
  the sprint it describes is done),
  `Documents/` (project notes migrated FROM SecondBrain in commit `fd2a641`:
  Roadmap, Marathon Route plan, Training Plan architecture, 2026-03 audit).
- SecondBrain (`~/SecondBrain`): there is **no 01-Projects folder anymore** —
  project docs were moved into this repo (`Documents/`). Relevant remaining notes:
  - `Daily/2026-06-09.md` — marathon-sprint wrap-up, migrations 12–14 confirmed on prod
  - `Daily/2026-06-29.md` — hillsrun.com brought back online (tunnel + :3001)
  - `Daily/2026-06-28.md` — homelab routing audit that found it down
  - `03-Resources/dev-notes/recherche-marathon-ajustement-dynamique.md` — adaptive-coach research
- Related projects: RecettesApp (shared theme + nutrition integration, paused),
  `~/Projects/homelab` (UM880 infra), `~/Projects/ladtc` (same tunnel model, port 3000).
- Remote: `git@github.com:StephRoos/HillsRun.git` (private). Auto-deploy via
  GitHub App `hillsrun-coolify`.
