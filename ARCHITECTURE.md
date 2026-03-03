# Technical Architecture: HillsRun

## Architecture Overview

**Philosophy**: Fullstack monorepo with Python async backend (FastAPI + asyncpg) and Next.js frontend with rich interactivity. Backend fetches Garmin data via OAuth token cycling. Frontend provides multi-user support (athletes + coaches) with server-side render performance and client-side PWA functionality. Designed for remote deployment on NAS via Cloudflare Tunnel.

**Stack Summary**:

| Layer | Technology |
|--------|------------|
| Backend Framework | FastAPI (async, ASGI) |
| Backend Database | asyncpg (raw SQL) + PostgreSQL |
| Backend Data Model | Pydantic v2 |
| Backend Package Manager | uv |
| Frontend Framework | Next.js 16 (App Router) |
| Frontend Language | TypeScript (strict) |
| Frontend UI | Tailwind CSS 4 + shadcn/ui |
| Frontend Database/ORM | Prisma 7 (auth & Garmin tables) |
| Frontend Auth | Better-Auth (multi-user, email/password, OAuth link) |
| Frontend Data fetching | TanStack Query (server-side + client-side) |
| Charts | Plotly.js (8 trend charts + activity splits) |
| PWA | Serwist service worker |
| Sync | Python fetchers (asyncio) + tenacity (retry/rate limiting) |
| External API | Garmin Connect (OAuth2, token refresh, rate limited) |
| Deployment Backend | Docker (ARM64) on UGREEN NAS, port 8100 |
| Deployment Frontend | Vercel (auto-deploy on git push) |
| Remote Access | Cloudflare Tunnel (api.hillsrun.com, SSH) |
| Testing | Vitest (frontend), pytest (backend — not yet implemented) |
| Theme | Shared with RecettesApp (dark mode default, next-themes) |

---

## Frontend Architecture

### Core Stack

- **Framework**: Next.js 16 (App Router)
  - **Why**: Same framework as RecettesApp. Server Components for dashboard SSR and SEO. App Router for scalability.
  - **Trade-off**: More complex than Vite SPA, but necessary for PWA + offline support + multi-user layout.

- **UI Components**: shadcn/ui + Tailwind CSS
  - **Why**: Pre-built accessible components. Fully customizable (copied into project). Consistent with RecettesApp.
  - **Trade-off**: More embedded code vs external library, but complete control over styling.

- **Charts**: Plotly.js (dynamic import, no SSR)
  - **Why**: Rich interactivity (zoom, hover tooltips, legend toggle). Activity split charts require client-side rendering.
  - **Trade-off**: ~500KB gzipped, loaded only on dashboard + trends pages. No SSR due to browser dependencies.

- **PWA**: Serwist service worker
  - **Why**: Offline workout logging, background sync. User continues viewing past activities during connection loss.
  - **Trade-off**: Service worker debugging is complex. Requires HTTPS (enforced by Vercel + Cloudflare).

### State Management

| State Type | Solution | Usage |
|-------------|----------|-------|
| **Server state** | TanStack Query | Garmin data (activities, daily, metrics), API pagination |
| **URL state** | nuqs (future) | Activity filters (type, date range), trends time period |
| **Form state** | React Hook Form | Not heavily used (minimal manual input) |
| **Local UI state** | useState/useContext | Modal open/close, coach context (who is viewing) |
| **Coach context** | React Context + header | Track "viewing as athlete" ID across pages |

**No Zustand/Redux**: Server state managed by TanStack Query + API caching. Coach access passed via React Context + HTTP header.

### Data Fetching Strategy

```
Page load (Server Component)
  → Verify user session (Better-Auth)
  → If coach: verify access to athlete (X-View-As-Athlete header)
  → Fetch latest Garmin summary from API (optional, for initial page state)
  → Pass to Client Component

User interactions (Client Component)
  → TanStack Query → /api/garmin/[route]
    → Next.js App Router /api/garmin/[...path]/route.ts
      → Inject X-API-Key (server-side)
      → Inject X-View-As-Athlete (if coach)
      → Proxy to http://nas:8100/api/[route]
        → FastAPI → asyncpg → PostgreSQL
          → Return Garmin data (daily, activities, metrics, etc.)
  → Cache with staleTime + manual invalidation

Sync trigger
  → User clicks "Sync Now" or logs in
  → Next.js API calls POST /api/garmin/sync
    → FastAPI /sync endpoint
      → Spawn threaded sync job (non-blocking)
      → Return "sync in progress"
  → TanStack Query polls sync status (manual invalidation on completion)
```

### Multi-User Architecture

**Athletes**: Own their Garmin data. Can allow coaches to view.

**Coaches**: Invited via email. Get dashboard showing all invited athletes. Can:
  - View athlete activities, daily metrics, trends
  - Create/edit planned workouts for athlete
  - Set coaching notes
  - Cannot modify athlete settings

**Implementation**:
- Server-side: Verify `X-View-As-Athlete` header in FastAPI (dependency injection)
- Client-side: React Context + UI toggle to switch viewing mode
- Database: `coaching_relationships` table + `invite_codes` for invitations

---

## Backend Architecture

### Core Stack

- **Framework**: FastAPI (async, ASGI)
  - **Why**: Native async/await. Pydantic v2 integration. OpenAPI docs. Lightweight.
  - **Trade-off**: Smaller ecosystem than Django, but sufficient for this scope.

- **Database**: PostgreSQL + asyncpg (raw SQL)
  - **Why**: asyncpg is the fastest Python PostgreSQL driver. Fine-grained control over queries (UPSERT, bulk insert).
  - **Trade-off**: Raw SQL is more verbose than ORM, but Garmin tables require UPSERT patterns for idempotence.

- **Garmin API Wrapper**: Garmin Connect OAuth + `garminconnect` library
  - **Why**: Established library (maintained). Handles login, token refresh, API endpoints.
  - **Trade-off**: Limited error handling, requires custom retry logic (tenacity).

- **Data Model**: Pydantic v2 + 30+ schemas
  - **Why**: Type-safe validation. Auto-generated OpenAPI docs. Schema reuse across routes.
  - **Trade-off**: Verbose for large payloads (e.g., activity with 500+ GPS points).

### API Layer

**Pattern**: Async route handlers with dependency injection

| Route Pattern | Handler | Purpose |
|-------|---------|---------|
| `GET /health` | `health_check()` | Simple liveness probe |
| `GET /daily/*` | `get_daily_summary()`, `get_heart_rate_*()`, etc. | Daily health metrics (read-only) |
| `GET /activities*` | `get_activities()`, `get_activity()` | Activity list + detail |
| `GET /metrics/*` | `get_fitness_metrics()`, `get_stress()`, etc. | Advanced metrics |
| `GET /planned_workouts` | `get_planned_workouts()` | Coach-set workouts |
| `POST /planned_workouts` | `create_planned_workout()` | Coach creates workout |
| `GET /sync/status` | `get_sync_status()` | Last sync timestamp + in-progress flag |
| `POST /sync` | `trigger_sync()` | Manual sync (user-initiated) |
| `GET /user/*` | `get_user_garmin_id()`, `get_profile()` | User settings |
| `GET /coaching/athletes` | `get_coached_athletes()` | Coach's athlete list |
| `POST /coaching/invite` | `create_invite_code()` | Invite athlete to coaching |

**Validation**: Pydantic on all inputs (request body + query params)

```python
# Example: pagination query validation
class PaginationParams(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)

async def get_activities(
    user_id: str = Depends(get_user_id),
    pagination: PaginationParams = Depends(),
    db: Connection = Depends(get_db),
):
    ...
```

### Authentication & Authorization

- **Provider**: Garmin OAuth2
  - **Why**: Users already have Garmin accounts. No separate password management.
  - **Method**: Authorization code flow. Token stored encrypted (Fernet) in DB.

- **API Key**: Internal backend-to-backend calls
  - **Method**: X-API-Key header (HMAC validation, timing-safe comparison)
  - **Storage**: Hardcoded in frontend .env, passed server-side only

- **Multi-User**: Session-based per user
  - **Athletes**: Full access to own data
  - **Coaches**: Limited via verify_coach_access() dependency
  - **Invite**: One-time code, email verification

### Database & Data Layer

- **Database**: PostgreSQL (self-hosted on NAS)
  - **Why**: Relational, excellent JSONB support for complex Garmin payloads (sleep stages, stress chart). Same tech as RecettesApp.

- **Async Driver**: asyncpg
  - **Why**: ~10x faster than psycopg2, native async/await. Perfect for FastAPI.
  - **Rejected alternative**: Databases (higher level, slower) or ORM (incompatible with UPSERT patterns).

### Data Model (Raw SQL + Pydantic)

**15+ Garmin tables** (managed by FastAPI, NOT Prisma):

```sql
-- Users & sync
garmin_user               # user_id, garmin_id, profile (JSONB)
sync_state               # user_id, last_sync, status

-- Daily summaries
daily_summary            # date, user_id, steps, calories, active_minutes
heart_rate_samples       # timestamp, user_id, bpm (1440 samples/day)
sleep_data               # date, user_id, duration, quality, sleep_levels (JSONB)
stress_data              # date, user_id, avg_stress, stress_chart (JSONB)
body_battery             # date, user_id, current, values (JSONB)

-- Body composition
body_composition         # date, user_id, weight, bmi, body_fat, muscle_mass

-- Advanced metrics
hrv_data                 # date, user_id, avg_hrv, weekly_avg
spo2_data                # date, user_id, avg_spo2, values (JSONB)
fitness_metrics          # date, user_id, vo2_max, lactate_threshold, recovery_time
respiration_data         # date, user_id, avg_respiration, values (JSONB)
hydration_data           # date, user_id, liters (Garmin-calculated)

-- Activities
activities               # id, user_id, start_time, type, duration, distance, calories
activity_splits          # activity_id, kilometer, duration, pace, heart_rate
planned_workouts         # id, coach_id, athlete_id, scheduled_date, type, description

-- Coaching
coaching_relationships   # coach_id, athlete_id, created_at
invite_codes            # code, coach_id, athlete_email, created_at, used_at

-- Auth (Prisma managed)
user                     # From BetterAuth
session                  # From BetterAuth
account                  # From BetterAuth (Garmin OAuth record)
verification             # From BetterAuth
```

**Key modeling choices**:

1. **UPSERT (ON CONFLICT DO UPDATE)**: All Garmin tables use idempotent upserts. Multiple runs of the same fetcher produce same DB state.

2. **JSONB for nested data**: Sleep stages, stress chart, spo2 values, body_battery values stored as JSONB arrays. Avoids 1-to-many explosion.

3. **Raw SQL**: Database.py uses asyncpg executemany() for bulk upserts (1000+ rows per query for heart rate). ORM would be slow.

4. **Pagination**: Page[T] Pydantic model wraps results. Frontend handles infinite scroll + TanStack Query.

5. **Garmin ID caching**: Lookup table (garmin_user) caches user_id → garmin_id (Garmin Connect requires garmin_id for most API calls).

### Sync Architecture

**Triggered by**:
1. User logs in (sync-on-login hook in Better-Auth)
2. User clicks "Sync Now" button
3. (Future) Scheduled daily sync

**Execution**:
1. FastAPI /sync endpoint receives request
2. Spawns threaded sync job (non-blocking, returns immediately)
3. Sync job runs async fetchers in parallel (daily, activities, body, metrics, wellness)
4. Each fetcher calls Garmin Connect API + upserts DB
5. Updates sync_state.last_sync
6. Frontend polls /sync/status (manual invalidation via TanStack Query)

**Fetchers** (src/fetchers/):
- BaseFetcher: Abstract base (retry logic, rate limiting via tenacity)
- DailyHealthFetcher: Heart rate, sleep, stress, body battery
- ActivitiesFetcher: Running/cycling/training activities + splits
- BodyCompositionFetcher: Weight, body fat, muscle mass
- AdvancedMetricsFetcher: HRV, SpO2, VO2 Max, lactate threshold
- WellnessFetcher: Respiration, hydration, training readiness

**Rate limiting**:
- Tenacity decorator: exponential backoff (max 5 retries, 1-32s delay)
- Garmin API: ~200 requests/day soft limit (fetchers stay well below)

---

## Database Schema

### Complete Physical Schema (PostgreSQL)

```sql
-- ===== USER MANAGEMENT (Garmin OAuth) =====

CREATE TABLE garmin_user (
  user_id TEXT PRIMARY KEY,
  garmin_id INT UNIQUE NOT NULL,
  display_name TEXT,
  profile JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sync_state (
  user_id TEXT PRIMARY KEY REFERENCES garmin_user(user_id),
  last_sync TIMESTAMPTZ,
  status TEXT DEFAULT 'idle', -- 'idle', 'in_progress', 'error'
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ===== DAILY SUMMARIES =====

CREATE TABLE daily_summary (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  steps INT,
  calories INT,
  active_minutes INT,
  highly_active_minutes INT,
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE heart_rate_samples (
  user_id TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  bpm INT,
  PRIMARY KEY (user_id, timestamp),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);
CREATE INDEX idx_heart_rate_samples_date ON heart_rate_samples(user_id, DATE(timestamp));

CREATE TABLE sleep_data (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  duration_seconds INT,
  quality INT, -- 1-5 scale
  sleep_levels JSONB, -- [{startTimeOffset: 0, duration: ..., type: 'light'}, ...]
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE stress_data (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  avg_stress INT,
  stress_chart JSONB, -- [{timeOffset: 0, stress_level: 25}, ...]
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE body_battery (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  current INT,
  values JSONB, -- [{timeOffset: 0, bodyBattery: 42}, ...]
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

-- ===== BODY COMPOSITION =====

CREATE TABLE body_composition (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  weight FLOAT,
  bmi FLOAT,
  body_fat FLOAT,
  muscle_mass FLOAT,
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

-- ===== ADVANCED METRICS =====

CREATE TABLE hrv_data (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  avg_hrv FLOAT,
  weekly_avg FLOAT,
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE spo2_data (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  avg_spo2 FLOAT,
  values JSONB, -- [{timeOffset: 0, spo2: 97}, ...]
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE fitness_metrics (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  vo2_max FLOAT,
  lactate_threshold FLOAT,
  recovery_time INT, -- hours
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE respiration_data (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  avg_respiration FLOAT,
  values JSONB, -- [{timeOffset: 0, respiration: 14.5}, ...]
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE hydration_data (
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  liters FLOAT,
  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);

-- ===== ACTIVITIES =====

CREATE TABLE activities (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  activity_type TEXT,
  duration_seconds INT,
  distance_meters INT,
  calories INT,
  avg_heart_rate INT,
  max_heart_rate INT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES garmin_user(user_id)
);
CREATE INDEX idx_activities_user_date ON activities(user_id, start_time DESC);

CREATE TABLE activity_splits (
  activity_id TEXT NOT NULL PRIMARY KEY,
  splits JSONB, -- [{kilometer: 1, duration: 245, pace: 4.08, heart_rate: 162}, ...]
  FOREIGN KEY (activity_id) REFERENCES activities(id)
);

-- ===== PLANNED WORKOUTS (COACHING) =====

CREATE TABLE planned_workouts (
  id TEXT PRIMARY KEY,
  coach_id TEXT NOT NULL,
  athlete_id TEXT NOT NULL,
  scheduled_date DATE NOT NULL,
  workout_type TEXT, -- 'easy_run', 'interval_training', 'long_run', etc.
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (athlete_id) REFERENCES garmin_user(user_id),
  FOREIGN KEY (coach_id) REFERENCES garmin_user(user_id)
);

-- ===== COACHING RELATIONSHIPS =====

CREATE TABLE coaching_relationships (
  coach_id TEXT NOT NULL,
  athlete_id TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (coach_id, athlete_id),
  FOREIGN KEY (coach_id) REFERENCES garmin_user(user_id),
  FOREIGN KEY (athlete_id) REFERENCES garmin_user(user_id)
);

CREATE TABLE invite_codes (
  code TEXT PRIMARY KEY,
  coach_id TEXT NOT NULL,
  athlete_email TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  used_at TIMESTAMPTZ,
  FOREIGN KEY (coach_id) REFERENCES garmin_user(user_id)
);

-- ===== AUTH TABLES (BetterAuth managed) =====
-- Prisma generates these; do NOT modify manually

CREATE TABLE "user" (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  emailVerified BOOLEAN DEFAULT false,
  image TEXT,
  createdAt TIMESTAMP DEFAULT now(),
  updatedAt TIMESTAMP DEFAULT now()
);

CREATE TABLE "session" (
  id TEXT PRIMARY KEY,
  userId TEXT NOT NULL,
  token TEXT UNIQUE NOT NULL,
  expiresAt TIMESTAMP NOT NULL,
  createdAt TIMESTAMP DEFAULT now(),
  updatedAt TIMESTAMP DEFAULT now(),
  FOREIGN KEY (userId) REFERENCES "user"(id)
);

CREATE TABLE "account" (
  id TEXT PRIMARY KEY,
  userId TEXT NOT NULL,
  accountId TEXT NOT NULL,
  providerId TEXT NOT NULL,
  accessToken TEXT,
  refreshToken TEXT,
  expiresAt TIMESTAMP,
  password TEXT,
  FOREIGN KEY (userId) REFERENCES "user"(id)
);

CREATE TABLE "verification" (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  value TEXT NOT NULL,
  expiresAt TIMESTAMP NOT NULL,
  createdAt TIMESTAMP DEFAULT now(),
  updatedAt TIMESTAMP DEFAULT now()
);
```

### Pydantic Schema Mirror (types/garmin.ts on frontend)

The frontend mirrors 242 lines of Pydantic schemas in `lib/types/garmin.ts`:

```typescript
// Mirrors FastAPI Pydantic responses
interface DailySummary {
  date: string;
  steps: number;
  calories: number;
  activeMinutes: number;
}

interface Activity {
  id: string;
  startTime: string;
  activityType: string;
  durationSeconds: number;
  distanceMeters: number;
  calories: number;
}

// ... 30+ more interfaces
```

---

## API Routes

### FastAPI Backend Routes (src/api/routers/)

| Route | Method | Handler | Purpose |
|-------|--------|---------|---------|
| `GET /health` | GET | health_check | Liveness probe |
| `GET /daily/summary/{user_id}` | GET | get_daily_summary | Today's steps, calories, active minutes |
| `GET /daily/heart-rate` | GET | get_heart_rate_today | 1440 BPM samples for today |
| `GET /daily/heart-rate/range` | GET | get_heart_rate_range | BPM samples for date range |
| `GET /daily/sleep/{date}` | GET | get_sleep_data | Sleep duration + quality + stages |
| `GET /daily/stress/{date}` | GET | get_stress_data | Average stress + hourly chart |
| `GET /daily/body-battery/{date}` | GET | get_body_battery | Current + hourly values |
| `GET /body/composition/{date}` | GET | get_body_composition | Weight, BMI, body fat, muscle |
| `GET /metrics/fitness` | GET | get_fitness_metrics | VO2 Max, lactate threshold |
| `GET /metrics/hrv` | GET | get_hrv_data | HRV daily + weekly average |
| `GET /metrics/spo2` | GET | get_spo2_data | SpO2 average + hourly values |
| `GET /metrics/respiration` | GET | get_respiration_data | Respiration rate + values |
| `GET /wellness/hydration` | GET | get_hydration_data | Daily water intake |
| `GET /activities` | GET | get_activities | List activities (paginated, filtered) |
| `GET /activities/{id}` | GET | get_activity | Activity detail + splits |
| `GET /planned-workouts` | GET | get_planned_workouts | Workouts for athlete (or coached by) |
| `POST /planned-workouts` | POST | create_planned_workout | Coach creates workout |
| `PUT /planned-workouts/{id}` | PUT | update_planned_workout | Coach updates |
| `DELETE /planned-workouts/{id}` | DELETE | delete_planned_workout | Coach deletes |
| `GET /sync/status` | GET | get_sync_status | Last sync + in-progress flag |
| `POST /sync` | POST | trigger_sync | Manual sync (user-initiated) |
| `GET /user/garmin-id` | GET | get_user_garmin_id | User's Garmin ID |
| `GET /user/profile` | GET | get_user_profile | User settings (name, timezone) |
| `GET /coaching/athletes` | GET | get_coached_athletes | Coach's athlete list |
| `POST /coaching/invite` | POST | create_invite_code | Invite athlete (one-time code) |
| `POST /coaching/accept` | POST | accept_invite | Athlete accepts invite |

### Next.js Frontend Proxy Routes (app/api/garmin/)

```
app/api/garmin/[...path]/route.ts
  → Intercepts: GET /api/garmin/daily/summary
  → Adds headers: X-API-Key, X-View-As-Athlete (if coach viewing athlete)
  → Proxies to: http://nas:8100/api/daily/summary
  → Returns response to client
```

### Better-Auth Routes (app/api/auth/)

```
app/api/auth/[...all]/route.ts
  → Handles: login, signup, signout, refresh token, OAuth callback
  → Uses Garmin OAuth provider (configured in lib/auth.ts)
  → Triggers sync-on-login hook
```

---

## Deployment Architecture

### Backend Deployment (Docker on UGREEN NAS)

**Container specifications**:
- **Base image**: python:3.11-slim (ARM64 compatible)
- **Port**: 8100
- **Env vars**: DB_URL (asyncpg), GARMIN_MFA (Garmin 2FA code), LOG_LEVEL

**Docker Compose** (on NAS):
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    ports:
      - "15432:5432"
    environment:
      POSTGRES_DB: hillsrun
      POSTGRES_PASSWORD: ...
    volumes:
      - pg_data:/var/lib/postgresql/data

  hillsrun-backend:
    build: .
    ports:
      - "8100:8000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:...@postgres:5432/hillsrun
      GARMIN_MFA: ...
    volumes:
      - ./src:/app/src  # Live reload for dev
```

**Cloudflare Tunnel** (NAS → api.hillsrun.com):
```yaml
tunnel: hillsrun
ingress:
  - hostname: api.hillsrun.com
    service: http://localhost:8100
  - service: http_status:404
```

### Frontend Deployment (Vercel)

- **Monorepo root**: `/` (Vercel detects `web/` as frontend)
- **Build command**: `cd web && pnpm install && pnpm build`
- **Output directory**: `web/.next`
- **Env vars**: `NEXT_PUBLIC_API_URL` (https://api.hillsrun.com), `BETTER_AUTH_SECRET`
- **Cron Jobs** (future): Nightly export to CSV (backup, analytics)

### Database Deployment (PostgreSQL on NAS)

- **Container**: postgres:16-alpine (ARM64)
- **Port**: 15432 (internal), tunneled via Cloudflare
- **Backup**: Daily pg_dump to NAS storage (cron job)
- **Connection pool**: Pgbouncer (planned, for high concurrency)

### Network Topology

```
User Browser
  ↓ HTTPS
Vercel Frontend (web.hillsrun.com)
  ↓ Fetch /api/garmin/* (server-side only)
Next.js API Proxy (Vercel)
  ↓ HTTP → Cloudflare Tunnel
Cloudflare Tunnel (api.hillsrun.com)
  ↓
UGREEN NAS (192.168.1.X:8100)
  ├── FastAPI Backend (port 8100)
  └── PostgreSQL (port 15432)
```

---

## Architecture Decision Records

### ADR-001: Garmin Tables NOT in Prisma

- **Context**: Garmin data model is complex (15+ tables with JSONB arrays). Prisma schema drift risk.
- **Decision**: Manage all Garmin tables via raw SQL migrations. Only auth tables via Prisma (BetterAuth).
- **Alternative**: Full Prisma schema including Garmin tables.
- **Reason**: `prisma db push` could accidentally drop Garmin tables. Raw SQL gives explicit control. Separation of concerns: Prisma = auth, SQL = Garmin data.
- **Consequence**: Must maintain migration files by hand. But Garmin tables are stable (append-only pattern).

### ADR-002: API Proxy Pattern (Next.js → FastAPI)

- **Context**: Frontend needs to call FastAPI backend. How to handle authentication?
- **Decision**: Next.js API proxy (`/api/garmin/*`) injects X-API-Key server-side, proxies to FastAPI.
- **Alternative**: Direct client call (exposes API key to browser), separate OAuth per frontend.
- **Reason**: API key stays secret (never in browser). Single auth layer. Easy to add rate limiting on proxy. Prepares for multi-frontend (mobile app could use same FastAPI).
- **Consequence**: Additional latency (~50ms), but acceptable. Requires env var management.

### ADR-003: Fernet Encryption for OAuth Tokens

- **Context**: Garmin OAuth refresh token must be stored in DB for token cycling.
- **Decision**: Encrypt with Fernet (symmetric, time-bound). Key in env var.
- **Alternative**: HSM, KMS (overkill), plain text (security risk).
- **Reason**: Fernet = built-in Python library. Tamper-proof. Automatic expiry checks. Simple to rotate key.
- **Consequence**: Single key required (no migration path if compromised), but suitable for self-hosted NAS.

### ADR-004: TanStack Query with Stale-Time + Manual Invalidation

- **Context**: Garmin data changes hourly (new activities, daily sync). When to refresh?
- **Decision**: staleTime=1 hour, queryFn=GET /api/garmin/activities. Manual invalidate on sync completion.
- **Alternative**: Polling every 5 min, real-time WebSocket, server-sent events.
- **Reason**: Polling = battery drain on mobile. WebSocket = complex for Vercel (stateless). Manual invalidate = precise, user-driven.
- **Consequence**: Users see stale data for up to 1 hour. Acceptable since Garmin sync is hourly anyway.

### ADR-005: Plotly.js with Dynamic Import (No SSR)

- **Context**: 8 trend charts + activity split charts require client-side rendering (state, zoom, legend).
- **Decision**: Dynamic import in use effect. No SSR. Loaded only on dashboard + trends pages.
- **Alternative**: SVG charts (lighter), Recharts (smaller), no charts (bare tables).
- **Reason**: Plotly = rich interactivity out-of-the-box (zoom, hover tooltips, legend toggle). Time-to-market over bundle size.
- **Consequence**: ~500KB gzipped, but lazy-loaded. Trade-off is acceptable for analytics UX.

### ADR-006: Coach Context via React Context + X-View-As-Athlete Header

- **Context**: Coach logs in, switches to view athlete X. How to pass context?
- **Decision**: React Context holds current athlete ID. TanStack Query injects X-View-As-Athlete header. FastAPI validates via verify_coach_access dependency.
- **Alternative**: URL param (?athleteId=...), server-side redirect, separate session.
- **Reason**: Header is invisible to user, less bookmark-breaking. Context allows UI to re-render quickly (coach sees athlete's data).
- **Consequence**: Requires careful invalidation (query key includes athleteId). But clean separation of concerns.

### ADR-007: Threaded Sync Jobs (Non-Blocking)

- **Context**: Sync job fetches 1000s of samples from Garmin API (5-10 min duration). Block HTTP response?
- **Decision**: Spawn threading.Thread for sync job. Return 202 Accepted immediately. Frontend polls /sync/status.
- **Alternative**: Celery, RQ (external task queue), blocking wait (timeout risk).
- **Reason**: Simplicity (no separate process). Threading = good enough for single NAS. FastAPI event loop stays unblocked.
- **Consequence**: Sync job can crash silently if not monitored. Add logging + error email (future).

### ADR-008: HillsRun Shared Theme (Dark Mode Default)

- **Context**: RecettesApp + HillsRun should share a visual identity.
- **Decision**: Dark theme by default (orange #FF8C00 primary, cyan #0891B2 accent, navy #0F1419 bg, slate #1A2332 cards). Light mode via next-themes toggle.
- **Alternative**: Light mode default, separate themes per app.
- **Reason**: Dark mode = athlete/fitness aesthetic. Consistent with sports apps (Strava, Garmin). Reduces eye strain during evening training planning.
- **Consequence**: Some users prefer light mode. Mitigated by next-themes toggle. Ensure contrast for accessibility.

---

## Complete Folder Structure

```
~/Projects/HillsRun/
├── PRD.md
├── ARCHITECTURE.md
├── .env.example                    # DB_URL, GARMIN_MFA, API_KEY_SECRET
├── src/                            # Python backend
│   ├── api/
│   │   ├── main.py                # FastAPI app, lifespan, DB init
│   │   ├── auth.py                # API key validation (X-API-Key, HMAC)
│   │   ├── dependencies.py        # get_db, get_user_id, verify_coach_access
│   │   ├── schemas.py             # 30+ Pydantic models, Page[T]
│   │   └── routers/
│   │       ├── health.py
│   │       ├── daily.py           # Heart rate, sleep, stress, body battery
│   │       ├── body.py            # Body composition
│   │       ├── metrics.py         # HRV, SpO2, VO2 Max, respiration
│   │       ├── activities.py      # Activities list + detail
│   │       ├── wellness.py        # Hydration, training readiness
│   │       ├── sync.py            # Trigger sync, status
│   │       ├── auth_garmin.py     # Garmin OAuth (login, callback)
│   │       ├── planned_workouts.py # Coach CRUD
│   │       ├── coaching.py        # Coaching relationships, invites
│   │       └── user.py            # User profile, Garmin ID
│   ├── database.py                # 1635 lines, 100+ async methods (upsert + query)
│   ├── garmin_client.py           # Garmin Connect API wrapper (retry + rate limiting)
│   ├── token_manager.py           # Fernet encryption for OAuth tokens
│   ├── sync_manager.py            # Orchestrates fetchers per category
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseFetcher (retry logic, rate limiting)
│   │   ├── daily_health.py        # Heart rate, sleep, stress, body battery
│   │   ├── activities.py          # Activities + splits
│   │   ├── body_comp.py           # Weight, body fat, muscle mass
│   │   ├── advanced_metrics.py    # HRV, SpO2, VO2 Max, lactate threshold
│   │   └── wellness.py            # Respiration, hydration
│   ├── config.py                  # Dataclass config (DB, Garmin, Sync, Logging)
│   ├── pyproject.toml             # uv dependencies
│   └── migrations/                # Raw SQL migrations (future: use Alembic)
├── web/                           # Next.js frontend
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── .env.example               # NEXT_PUBLIC_API_URL, BETTER_AUTH_SECRET
│   ├── prisma/
│   │   ├── schema.prisma          # Auth tables + Garmin tables (schema-only)
│   │   └── migrations/            # Auth table migrations (Prisma-managed)
│   └── src/
│       ├── app/
│       │   ├── layout.tsx         # Root layout (QueryProvider, AuthProvider, ThemeProvider)
│       │   ├── (auth)/
│       │   │   ├── layout.tsx     # No sidebar
│       │   │   ├── login/page.tsx
│       │   │   └── signup/page.tsx
│       │   ├── (dashboard)/
│       │   │   ├── layout.tsx     # Sidebar layout
│       │   │   ├── page.tsx       # Dashboard (summary cards, 8 trend charts)
│       │   │   ├── calendar/page.tsx    # Activity calendar
│       │   │   ├── trends/page.tsx      # Detailed trend analysis
│       │   │   ├── settings/page.tsx    # User settings, coach management
│       │   │   ├── activity/
│       │   │   │   └── [id]/page.tsx    # Activity detail + splits
│       │   │   └── coaching/
│       │   │       ├── athletes/page.tsx # Coach's athletes
│       │   │       └── workouts/page.tsx # Planned workouts
│       │   └── api/
│       │       ├── auth/[...all]/route.ts    # Better-Auth catch-all
│       │       └── garmin/[...path]/route.ts # Proxy to FastAPI
│       ├── actions/
│       │   ├── auth.ts            # Sync-on-login (trigger backend sync)
│       │   └── coaching.ts        # Accept invite, etc.
│       ├── components/
│       │   ├── ui/                # shadcn/ui (button, card, modal, etc.)
│       │   ├── dashboard/
│       │   │   ├── summary-cards.tsx
│       │   │   ├── trend-charts.tsx      # Plotly.js dynamic import
│       │   │   └── sync-status.tsx
│       │   ├── activity/
│       │   │   ├── activity-card.tsx
│       │   │   ├── activity-splits.tsx
│       │   │   └── activity-map.tsx      # Polyline from GPS
│       │   ├── calendar/
│       │   │   └── activity-calendar.tsx
│       │   ├── coaching/
│       │   │   ├── athlete-switch.tsx
│       │   │   └── workout-list.tsx
│       │   └── layout/
│       │       ├── sidebar.tsx
│       │       └── header.tsx
│       ├── hooks/
│       │   ├── use-activities.ts       # TanStack Query
│       │   ├── use-metrics.ts
│       │   ├── use-trends.ts
│       │   ├── use-planned-workouts.ts
│       │   ├── use-garmin-account.ts
│       │   ├── use-coaching.ts
│       │   ├── use-sync.ts
│       │   ├── use-vma.ts              # VO2 Max calculations
│       │   ├── use-online-status.ts    # Service worker + IndexedDB
│       │   └── use-pwa.ts              # PWA install prompt
│       ├── lib/
│       │   ├── auth.ts            # Better-Auth server config, sync-on-login hook
│       │   ├── auth-client.ts     # Better-Auth React client
│       │   ├── prisma.ts          # Singleton Prisma client
│       │   ├── garmin-api.ts      # Type-safe HTTP client (45+ methods)
│       │   ├── garmin-user.ts     # Resolve garmin_user_id (cached, deduplicated)
│       │   ├── coach-access.ts    # Server-side coach access verification
│       │   ├── coach-context.tsx  # React Context for coach viewing
│       │   ├── utils.ts           # Formatting helpers, ACTIVITY_COLORS
│       │   └── types/
│       │       ├── garmin.ts      # 242 lines, mirrors Pydantic schemas
│       │       └── auth.ts
│       ├── public/
│       │   ├── manifest.json      # PWA metadata
│       │   └── sw.ts              # Serwist service worker
│       └── styles/
│           └── globals.css        # Tailwind + HillsRun theme
├── docker-compose.yml              # Backend + DB containers
├── Dockerfile                       # Python 3.11 slim, ARM64
└── README.md
```

---

## Key Files (Lines of Code Estimates)

| File | Lines | Purpose |
|------|-------|---------|
| `src/database.py` | 1635 | Async DB methods (upsert, query, multi-user) |
| `src/api/schemas.py` | 800 | 30+ Pydantic models |
| `web/lib/garmin-api.ts` | 500 | 45+ HTTP methods |
| `web/lib/types/garmin.ts` | 242 | TypeScript mirror of Pydantic |
| `web/src/components/dashboard/trend-charts.tsx` | 300 | 8 Plotly charts |
| `web/src/hooks/use-activities.ts` | 50 | TanStack Query hook |
| (Full backend) | ~3000 | FastAPI + fetchers + DB |
| (Full frontend) | ~5000 | Next.js + components + hooks |

---

## Testing

### Frontend Testing (Vitest + React Testing Library)

**Status**: 3 test files, 15 tests

```
web/src/lib/
  ├── use-online-status.test.ts     # Service worker status
  ├── offline-indicator.test.tsx     # Component rendering
  └── utils.test.ts                  # Formatting helpers (pace, distance)
```

**Commands**:
```bash
pnpm test                 # Run once
pnpm test:watch          # Watch mode
pnpm test --coverage     # Coverage report
```

### Backend Testing (pytest — not yet implemented)

**Future**: Add pytest fixtures for database + mocks for Garmin API

```
src/tests/
  ├── test_database.py    # Upsert, query, multi-user
  ├── test_sync_manager.py # Sync orchestration
  ├── test_fetchers.py    # Fetcher logic
  └── test_api.py         # Route validation
```

**Commands** (future):
```bash
uv run pytest           # Run tests
uv run pytest -xvs      # Verbose + stop on first failure
uv run pytest --cov     # Coverage report
```

---

## Cost Estimation

### Development (v1 solo, self-hosted)

| Service | Cost | Note |
|---------|------|------|
| UGREEN NAS (one-time) | ~150€ | 4TB storage, ARM64 CPU |
| Cloudflare Tunnel | Free | 1 tunnel, unlimited bandwidth |
| PostgreSQL (self-hosted) | Free | Docker on NAS |
| Garmin Connect API | Free | No commercial API, requires account |
| Vercel (frontend) | Free | Hobby plan, up to 100GB bandwidth/month |
| **Total dev** | **~0€/month** | (NAS amortized over 5 years = ~30€/month) |

### Production (future: multiple athletes)

| Service | Estimated Cost | Note |
|---------|-------------|------|
| UGREEN NAS (amortized) | ~30 €/month | 4TB, 5-year lifespan |
| Cloudflare Tunnel | Free | Included in free plan |
| PostgreSQL (self-hosted) | Free | Backup power, disk wear |
| Vercel Pro | ~20 €/month | If exceeding free tier (100GB/month) |
| Domain | ~12 €/year | .com or .fr |
| **Total prod** | **~50 €/month** | For 10+ athletes |

**Hardware**:
- UGREEN NAS: 2 × 4TB HDD (RAID-1), 4-core CPU, 4GB RAM (sufficient for 20+ concurrent syncs)
- Electricity: ~30W baseline, ~100W under load. EU rate ~0.25€/kWh → ~20€/month continuous

**Scaling limits**:
- PostgreSQL on NAS: Can handle ~1000 daily queries (not optimized yet)
- NAS network: Gigabit LAN, no cloud egress fees (unlike AWS/GCP)
- Vercel: Free tier handles 100+ athletes (stateless)
- Garmin API: ~200 requests/day soft limit (per user, not strict)

---

## Summary

**HillsRun** is a full-featured athlete fitness tracker with coach collaboration. It combines:

1. **Backend strength**: Async FastAPI for Garmin sync, raw SQL UPSERT for idempotence, Fernet encryption for tokens.
2. **Frontend strength**: PWA with Serwist, multi-user via context + headers, rich Plotly charts.
3. **Deployment**: Self-hosted on NAS (cost-effective), Cloudflare Tunnel (secure), Vercel frontend (fast).
4. **Architecture**: Minimal dependencies (no task queue, no WebSocket), explicit data flow (query → sync → invalidate).

### Training Plan Engine

The training plan engine generates periodized plans from athlete profile, race target, and fitness data.

**Core modules** (`src/training/`):
- `models.py` — Pydantic models: `DayPreferences`, `GeneratePlanRequest`, `SessionSpec`, `RaceFlags`, enums
- `week_builder.py` — Weekly session placement with constraint-based scheduling
- `plan_generator.py` — Orchestrates multi-week plan generation, resolves preferences
- `session_catalog.py` — Session templates by type/phase/experience
- `race_classifier.py` — Classifies races (trail categories, D+, technical, altitude)
- `long_run_calculator.py` — Progressive long run distance/duration targets

**Day Preferences** (`DayPreferences` model):
Athletes can configure preferred days for each session category:
- `long_run: int` — Single day (1-7) for the weekly long run
- `quality: list[int]` — Up to 3 days for hard sessions (tempo, intervals, hill repeats)
- `easy_run: list[int]` — Preferred days for easy/recovery runs (when more available days than session slots)
- `strength: list[int]` — Up to 2 days for cross-training (RMU)

Preferences are best-effort: safety constraints always override:
- Max 2 consecutive hard days; 3rd day must be recovery
- No hard session the day after a long run (wrap-around: Sun→Mon)
- Strength (cross-training) allowed on any day including recovery days
- Resolution priority: per-plan override > profile stored > engine defaults

**Frontend** (`web/src/components/training-plan/day-preference-picker.tsx`):
Interactive 7×N grid where athletes configure session placement:
- Long Run (orange), Quality (red), Easy Run (blue), Strength (cyan)
- Status summary row: REC (green, easy run day) / REST (gray, no session)
- Auto-computes EF slots from `maxRunningSessions - allocated`; interactive when choice needed
- Blocked days (post-SL, post-2-quality) disabled for hard sessions

**Next milestones**:
- Backend tests (pytest + mocks)
- Mobile app (Expo, reuse FastAPI)
- Integration with RecettesApp (shared nutrition data)
