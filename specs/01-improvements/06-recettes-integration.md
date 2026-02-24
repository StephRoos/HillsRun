# Task 06: RecettesApp Integration Design

**Status**: Design complete — implementation in future phase
**Date**: 2026-02-24

---

## Context

RecettesApp and HillsRun are part of the same athlete ecosystem. HillsRun knows how hard an athlete trained today. RecettesApp manages their nutrition. The integration goal is bidirectional data sharing:

- **HillsRun → RecettesApp**: Daily training load (calories burned, TSS) → adjust meal planning calorie targets
- **RecettesApp → HillsRun**: Nutrition intake → training readiness context (future)

Both apps already share:
- Same tech stack (Next.js 16, Better-Auth, PostgreSQL, shadcn/ui, Tailwind, same dark theme)
- Same deployment model (Vercel frontend, self-hosted backend)
- Same Better-Auth schema for user management

---

## 1. Shared Authentication Strategy

### Decision: Cross-service API key + shared Better-Auth DB

**Rationale**: The simplest option that avoids full SSO while keeping apps deployable independently.

**Architecture**:
```
User logs into RecettesApp (Better-Auth, own DB)
  → RecettesApp fetches calorie goal from HillsRun API
    → Authorization: Bearer <HILLSRUN_API_KEY>
    → X-Better-Auth-User-Id: <user.id from shared Better-Auth>
  → HillsRun resolves user_id from Better-Auth ID
  → Returns calorie data
```

**Options considered**:

| Option | Pros | Cons |
|--------|------|------|
| A. Shared Better-Auth DB (same Postgres) | Single user identity, no token exchange | Tight coupling, shared DB risks |
| B. API key + user ID header (chosen) | Loose coupling, each app independent | Requires user ID to be shared in client |
| C. OAuth between apps | Proper SSO | Complex, overkill for 2 apps + 1 developer |
| D. Merge into single app | One codebase | Massive refactor, loses separation of concerns |

**Chosen approach (B)**:
- RecettesApp stores the HillsRun API key in its backend `.env`
- RecettesApp sends `X-Better-Auth-User-Id` header with requests (since both apps use Better-Auth, user IDs are compatible if they share the same PostgreSQL instance or sync user records)
- No client-side token exposure

**Constraint**: Both apps must use the same Better-Auth instance OR share user IDs via email-based lookup. The cleanest initial path: both apps connect to the same PostgreSQL database and the same `user` table managed by Better-Auth.

---

## 2. API Contract: HillsRun Exposes Daily Calorie Goal

### Endpoint: `GET /api/v1/nutrition/daily-goal`

**Purpose**: Return the recommended daily calorie intake based on today's training load.

**Request**:
```
GET /api/v1/nutrition/daily-goal?date=2026-02-24
X-API-Key: <HILLSRUN_API_KEY>
X-Better-Auth-User-Id: <better_auth_user_id>
```

**Response** (`200 OK`):
```json
{
  "date": "2026-02-24",
  "base_bmr_calories": 1800,
  "active_calories": 650,
  "total_training_calories": 650,
  "recommended_daily_intake": 2450,
  "training_load": {
    "tss": 72,
    "duration_minutes": 65,
    "activity_type": "trail_running",
    "intensity": "moderate"
  },
  "adjustment_factor": 1.36
}
```

**Formula**: `recommended_daily_intake = base_bmr + active_calories * 1.1` (10% margin for recovery)

**Response** (`204 No Content`): No Garmin data for this user/date — RecettesApp uses default targets.

**Response** (`404 Not Found`): No Garmin account linked to this Better-Auth user.

### Pydantic Schema (HillsRun backend)

```python
class NutritionDailyGoal(BaseModel):
    date: date
    base_bmr_calories: Optional[int] = None
    active_calories: Optional[int] = None
    total_training_calories: Optional[int] = None
    recommended_daily_intake: Optional[int] = None
    training_load: Optional[dict] = None
    adjustment_factor: Optional[float] = None
```

### TypeScript Schema (RecettesApp client)

```typescript
interface NutritionDailyGoal {
  date: string;
  base_bmr_calories: number | null;
  active_calories: number | null;
  total_training_calories: number | null;
  recommended_daily_intake: number | null;
  training_load: {
    tss: number | null;
    duration_minutes: number | null;
    activity_type: string | null;
    intensity: string | null;
  } | null;
  adjustment_factor: number | null;
}
```

---

## 3. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Browser                                 │
│                                                                      │
│   ┌─────────────────┐              ┌─────────────────────────────┐  │
│   │   HillsRun      │              │       RecettesApp           │  │
│   │  (web.hillsrun) │              │  (web.recettes-app.com)     │  │
│   └────────┬────────┘              └──────────────┬──────────────┘  │
└────────────┼──────────────────────────────────────┼─────────────────┘
             │                                      │
    (Better-Auth session)              (Better-Auth session)
             │                                      │
             ▼                                      ▼
┌────────────────────────┐           ┌───────────────────────────────┐
│   HillsRun Backend     │           │    RecettesApp Backend        │
│   (api.hillsrun.com)   │◄──────────│    (api.recettes-app.com)     │
│                        │  GET      │                               │
│  /api/v1/nutrition/    │  /nutrition│  Adds:                       │
│    daily-goal          │  /daily-  │  X-API-Key: <shared_key>     │
│                        │  goal     │  X-Better-Auth-User-Id: uid  │
│  Reads:                │           │                               │
│  - daily_summary       │           │  Uses response to set:       │
│  - activities          │           │  → daily calorie target      │
│  - garmin_user         │           │  → meal plan adjustments     │
└───────────┬────────────┘           └───────────────────────────────┘
            │
            ▼
┌───────────────────────┐
│   PostgreSQL (shared) │
│                       │
│  - user (Better-Auth) │◄── Both apps resolve user identity here
│  - garmin_user        │
│  - daily_summary      │
│  - activities         │
│  - recettes tables    │
│    (future)           │
└───────────────────────┘
```

---

## 4. Implementation Phases

### Phase 1: Shared Auth (1-2 days)

**Goal**: Both apps use the same PostgreSQL database for Better-Auth tables.

**Tasks**:
1. Configure RecettesApp's Better-Auth to point to HillsRun's PostgreSQL instance
2. Create a dedicated PostgreSQL user with read/write access to auth tables only
3. Verify session tokens are compatible (same `BETTER_AUTH_SECRET` or separate instances with shared DB)
4. Test: User registered in HillsRun can also sign in to RecettesApp with same credentials

**Config change in RecettesApp**:
```
DATABASE_URL=postgresql://shared_user:pass@db.hillsrun.com:15432/hillsrun
```

**Security note**: Use a separate PostgreSQL role with GRANT on auth tables only:
```sql
CREATE ROLE recettes_app LOGIN PASSWORD 'secure_pass';
GRANT SELECT, INSERT, UPDATE, DELETE ON "user", session, account, verification TO recettes_app;
```

### Phase 2: HillsRun Nutrition Endpoint (1 day)

**Goal**: Implement `GET /api/v1/nutrition/daily-goal` in HillsRun FastAPI.

**Files to create/modify**:
- `src/api/routers/nutrition.py` (new router)
- `src/database.py` (add `query_nutrition_goal()` method)
- `src/api/schemas.py` (add `NutritionDailyGoal` schema)
- `src/api/main.py` (include new router)

**Implementation**:
```python
@router.get("/daily-goal")
async def get_daily_calorie_goal(
    date: date = Query(default_factory=date.today),
    db: Database = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> NutritionDailyGoal:
    summary = await db.query_daily_summary(user_id, date)
    if not summary:
        return Response(status_code=204)

    active_cals = summary.get("active_calories", 0) or 0
    bmr = summary.get("bmr_calories", 1800) or 1800
    recommended = int(bmr + active_cals * 1.1)

    return NutritionDailyGoal(
        date=date,
        base_bmr_calories=bmr,
        active_calories=active_cals,
        recommended_daily_intake=recommended,
        adjustment_factor=round(recommended / bmr, 2) if bmr else None,
    )
```

### Phase 3: RecettesApp HillsRun Client (1 day)

**Goal**: RecettesApp fetches calorie goal from HillsRun API on meal planning pages.

**Files in RecettesApp** (out of HillsRun scope):
- `lib/hillsrun-api.ts` — HTTP client for HillsRun API
- `hooks/use-training-calories.ts` — TanStack Query hook
- Environment variable: `HILLSRUN_API_URL`, `HILLSRUN_API_KEY`

**HTTP client pattern**:
```typescript
// lib/hillsrun-api.ts
export const hillsrunApi = {
  getDailyCalorieGoal: async (date: string, userId: string) => {
    const res = await fetch(
      `${process.env.HILLSRUN_API_URL}/api/v1/nutrition/daily-goal?date=${date}`,
      {
        headers: {
          "X-API-Key": process.env.HILLSRUN_API_KEY!,
          "X-Better-Auth-User-Id": userId,
        },
      }
    );
    if (res.status === 204) return null; // no Garmin data
    if (!res.ok) throw new Error("Failed to fetch training calories");
    return res.json() as Promise<NutritionDailyGoal>;
  },
};
```

### Phase 4: RecettesApp UI Integration (0.5 days)

**Goal**: Display training-adjusted calorie target in RecettesApp meal planning UI.

**UI changes** (out of HillsRun scope):
- Meal planning page: Show "Training day target: 2,450 kcal (↑ 650 kcal from training)"
- Daily macro breakdown adjusts proportionally to training load
- Empty state if HillsRun API is unavailable (graceful degradation)

---

## 5. Security

### API Key Exchange

```
HILLSRUN_API_KEY=<generated with openssl rand -hex 32>
```

- Stored in RecettesApp backend environment only (never in frontend)
- HillsRun verifies via `X-API-Key` header (same HMAC mechanism as existing auth)
- Rotate monthly or on security events

### CORS Configuration

HillsRun FastAPI currently only serves server-to-server requests. No CORS changes needed if RecettesApp backend proxies requests (recommended).

If direct browser-to-HillsRun calls are needed (not recommended), add:
```python
# src/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web.recettes-app.com"],
    allow_methods=["GET"],
    allow_headers=["X-API-Key", "X-Better-Auth-User-Id"],
)
```

### Rate Limiting

Add per-app rate limiting on the nutrition endpoint to prevent abuse:
```python
# Limit RecettesApp to 100 requests/day per user
# (Daily goal doesn't change more than once per sync)
```

---

## 6. Error Handling and Degradation

RecettesApp must handle HillsRun being unavailable gracefully:

```typescript
// hooks/use-training-calories.ts
export function useTrainingCalories(date: string) {
  return useQuery({
    queryKey: ["training-calories", date],
    queryFn: () => hillsrunApi.getDailyCalorieGoal(date, session.user.id),
    staleTime: 1000 * 60 * 60, // 1 hour
    retry: 1,
    // On error: return null, use default calorie targets
    onError: () => null,
  });
}
```

**Degradation**: If HillsRun API is down, RecettesApp falls back to user's configured base calorie target (no training adjustment).

---

## 7. Success Criteria

- [ ] Phase 1: Same Better-Auth credentials work in both apps
- [ ] Phase 2: `GET /api/v1/nutrition/daily-goal` returns correct calorie data
- [ ] Phase 2: Endpoint has integration test coverage
- [ ] Phase 3: RecettesApp fetches and caches training calorie data
- [ ] Phase 4: Meal planning UI shows training-adjusted targets
- [ ] Security: API key rotated and stored securely in both apps
- [ ] Degradation: RecettesApp works normally when HillsRun is offline

---

## 8. Timeline Estimate

| Phase | Effort | Prerequisites |
|-------|--------|--------------|
| Phase 1: Shared Auth | 1-2 days | HillsRun + RecettesApp stable |
| Phase 2: HillsRun API endpoint | 1 day | Phase 1 complete |
| Phase 3: RecettesApp client | 1 day | Phase 2 deployed |
| Phase 4: RecettesApp UI | 0.5 days | Phase 3 complete |
| **Total** | **3.5-4.5 days** | |

---

## Dependencies

**Must complete first**: HillsRun tasks 01-05 (backend tests, security hardening, CI/CD)
**Blocks**: Actual implementation (Phase 1-4 above)

## Related Documentation

- `ARCHITECTURE.md` — ADR-002 (API proxy), ADR-006 (coach context via headers)
- `docs/SCHEMA.md` — Database schema reference
- `docs/SETUP.md` — NAS deployment guide
