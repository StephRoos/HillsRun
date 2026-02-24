# HillsRun Performance Audit

**Date**: 2026-02-24
**Build**: Next.js 16.1.6 (webpack)

---

## 1. Bundle Analysis

### Build output (pnpm build)

```
Route (app)
 ○  /               (Static)
 ○  /_not-found     (Static)
 ○  /~offline       (Static, PWA offline page)
 ƒ  /activity/[id]  (Dynamic, server-rendered)
 ƒ  /calendar       (Dynamic)
 ƒ  /dashboard      (Dynamic)
 ○  /login          (Static)
 ƒ  /settings       (Dynamic)
 ○  /signup         (Static)
 ƒ  /trends         (Dynamic)
```

### Chunk sizes (uncompressed, from .next/static/chunks/)

| Chunk | Size | Contents |
|-------|------|----------|
| `3fc5fe80.*.js` | **~1.5 MB** | Plotly.js basic-dist (was 4.4 MB with full build) |
| `4258e3df-*.js` | 196 KB | app-router internals |
| `5366-*.js` | 192 KB | React + dependencies |
| `framework-*.js` | 188 KB | Next.js framework |
| `7638-*.js` | 140 KB | TanStack Query + misc |
| `main-*.js` | 136 KB | App entry point |
| `polyfills-*.js` | 112 KB | Browser polyfills |

### Key observation
The **~1.5 MB Plotly chunk** (down from 4.4 MB) uses `plotly.js-basic-dist` which supports scatter, bar, and pie charts — all chart types used in this app. This is expected and by design (ADR-005): Plotly.js is loaded dynamically (no SSR), so it is only downloaded when the user visits a chart-heavy page (`/trends` or `/activity/[id]`).

Serwist service worker no longer warns about the Plotly chunk size exceeding the precache threshold.

---

## 2. Plotly.js — Tree-shaking Assessment

**Current implementation**: Custom Plotly wrapper via `next/dynamic` with `{ ssr: false }`.

```typescript
// web/src/lib/plotly.ts
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";
const Plot = createPlotlyComponent(Plotly);
export default Plot;

// Usage in chart components:
const Plot = dynamic(() => import("@/lib/plotly"), { ssr: false });
```

**Tree-shaking status**: Plotly.js does NOT support tree-shaking. `plotly.js-basic-dist` (~1.5 MB) is used instead of the full bundle (~4.5 MB). This covers all chart types used in the app: scatter, bar.

**Chart types supported by basic-dist**: scatter, bar, pie, histogram.

**Error boundaries**: All chart components are wrapped with `<ErrorBoundary>` + `<Suspense>` to catch rendering failures without crashing the page. Chart fallbacks show a friendly "Impossible de charger le graphique" message with a retry button.

**Alternatives if bundle size becomes critical**:
- Migrate to Recharts or Nivo (smaller, tree-shakeable, but less interactive)

---

## 3. Image Optimization

**Current status**: No `<Image>` components from `next/image` are used (no static images in the app — all content is data-driven charts and text).

**Garmin profile avatars**: Not currently displayed. When implemented, use `next/image` with proper `width`/`height` and `priority` on above-the-fold images.

**Recommendation**: No action needed currently. Add `next/image` when/if user avatars are implemented.

---

## 4. TanStack Query Caching Effectiveness

**Strategy**: `staleTime` + manual invalidation after mutations (ADR-004). No polling.

### staleTime

| Query | staleTime | Invalidation trigger |
|-------|-----------|---------------------|
| Activities | 1 hour | Sync completion |
| Daily summary | 1 hour | Sync completion |
| HRV / sleep / body battery | 1 hour | Sync completion |
| Training readiness | 1 hour | Sync completion |
| VMA | Infinity | User update |
| Sync status | 30 seconds | Manual sync trigger |
| Coaching status | 5 minutes | Coach action |

### gcTime (memory retention after inactive)

| Query | gcTime | Rationale |
|-------|--------|-----------|
| Activities (list, detail, splits) | 30 minutes | Large paginated responses — avoid re-fetching on navigation |
| Metric hooks (HRV, sleep, stress, body battery, fitness, body composition, daily summary, training readiness) | 1 hour | Historical data — changes only after sync |
| VMA | Infinity | Rarely changes — user-set value |
| Coaching status / invite codes | 10 minutes | Session-scoped data |
| Sync status | Default (5 min) | Frequently polled, no benefit from longer retention |

**Assessment**: The caching strategy is well-suited to Garmin data (synced hourly at most). No unnecessary re-fetches observed. The `queryKey` includes all relevant params (date range, limit, athlete ID), ensuring correct cache separation for multi-user (coach/athlete) scenarios.

---

## 5. API Response Times (Key Endpoints)

Measured on NAS deployment (UGREEN NAS, ARM64, asyncpg + PostgreSQL):

| Endpoint | Typical latency | Notes |
|----------|----------------|-------|
| `GET /api/v1/daily/summary` | ~30-80ms | Single row query |
| `GET /api/v1/activities` | ~50-120ms | Paginated, indexed |
| `GET /api/v1/activities/{id}` | ~20-60ms | PK lookup |
| `GET /api/v1/activities/{id}/splits` | ~15-40ms | PK lookup |
| `GET /api/v1/metrics/hrv` | ~30-80ms | Date-range scan |
| `GET /api/v1/sync/status` | ~20-50ms | Small table |
| `POST /api/v1/sync/trigger` | ~5-20ms | Spawns thread, returns immediately |

**Network overhead**: Cloudflare Tunnel adds ~30-50ms round-trip (NAS → Cloudflare PoP → Browser). Total perceived latency = API latency + tunnel overhead + Next.js proxy overhead (~5-10ms).

**Bottleneck**: The largest latency source is the Cloudflare Tunnel, not the API itself. No database query optimization is needed at current scale (single user).

---

## 6. Cache-Control Strategy

HTTP `Cache-Control` headers are set by `CacheControlMiddleware` in `src/api/middleware.py`.

### Rules

| Endpoint group | Condition | Cache-Control |
|----------------|-----------|---------------|
| `/api/v1/daily/*` | `end_date` < today | `public, max-age=86400` (24 h) |
| `/api/v1/body/*` | `end_date` < today | `public, max-age=86400` (24 h) |
| `/api/v1/metrics/*` | `end_date` < today | `public, max-age=86400` (24 h) |
| `/api/v1/activities` | `end_date` < today | `public, max-age=86400` (24 h) |
| All cacheable endpoints | `end_date` == today or absent | `private, max-age=300` (5 min) |
| `/api/v1/sync/*` | always | `no-store` |
| `/api/v1/auth/*` | always | `no-store` |
| `/api/v1/coaching/*` | always | `no-store` |
| `/api/v1/nutrition/*` | always | `no-store` |

### Rationale

- **Historical data is immutable**: Garmin data for past dates never changes once synced. `public, max-age=86400` allows Cloudflare Tunnel / CDN edges to cache responses for 24 hours.
- **Today's data may still be updated**: Sync can run at any time, so current-day data uses a short private cache (5 min).
- **Sync / auth / coaching must never be cached**: These endpoints reflect mutable or sensitive state.

---

## 7. Recommendations

### Immediate (low effort)

1. **Serwist precache exclusion**: Already handled — the 4.61 MB Plotly chunk is correctly excluded from SW precaching via the `maximumFileSizeToCacheInBytes` warning. No action needed; this is expected behavior.

2. **Font optimization**: Verify `next/font` is used for any custom fonts. Currently using Tailwind defaults (system font stack) — no Google Fonts CDN calls, which is optimal.

3. **Compression**: Ensure Vercel serves `.br` (Brotli) compressed bundles. Brotli compresses the 4.4 MB Plotly chunk to ~1.2 MB. Vercel does this automatically.

### Medium-term (moderate effort)

4. ~~**Plotly partial import**~~: Done — switched to `plotly.js-basic-dist` (~1.5 MB, down from ~4.4 MB). Error boundaries added on all chart components.

5. ~~**Edge caching for static metrics**~~: Done — `CacheControlMiddleware` adds `Cache-Control: public, max-age=86400` for historical date queries on all daily/body/metrics/activities endpoints.

6. ~~**gcTime tuning for large paginated queries**~~: Done — activity list hooks use 30 min gcTime; metric hooks use 1 hour; VMA uses Infinity; coaching hooks use 10 min.

7. **Virtual scrolling for activity list**: If activity lists grow beyond 200 items, consider `@tanstack/react-virtual` for the `/calendar` and `/dashboard` activity lists.

8. **API pagination caching**: Consider implementing cursor-based pagination (instead of limit/offset) to enable infinite query cache merging in TanStack Query.

### Long-term (significant effort)

9. **Database connection pooling**: Add PgBouncer between FastAPI and PostgreSQL when scaling beyond 5 concurrent users. Current asyncpg pool (min=1, max=5) is sufficient for single-user.

---

## 8. Build Warnings

| Warning | Severity | Action |
|---------|----------|--------|
| Serwist: Plotly chunk precache | Info | Resolved — basic-dist is ~1.5 MB, within precache threshold |
| Better-Auth base URL not set | Warning | Set `BETTER_AUTH_BASE_URL` env var in Vercel |
| Compiled with warnings | Warning | Due to above warnings, not code issues |

---

## Summary

The Plotly bundle has been reduced from ~4.4 MB to ~1.5 MB by switching to `plotly.js-basic-dist`. All chart types used in the app (scatter, bar) are supported by the basic distribution. Plotly remains lazy-loaded (dynamic import, no SSR).

Error boundaries have been added to all chart components (`/trends`, `/activity/[id]`) using React `ErrorBoundary` class components + `React.Suspense` with `ChartSkeleton` fallbacks. Chart rendering failures are now isolated and do not crash the full page.

`Cache-Control` headers are now set by `CacheControlMiddleware` on all data endpoints. Historical queries (end_date before today) return `public, max-age=86400`; current-day queries return `private, max-age=300`; sync/auth/coaching/nutrition return `no-store`.

TanStack Query `gcTime` has been tuned: activity hooks (30 min), metric hooks (1 hour), VMA (Infinity), coaching hooks (10 min). This reduces re-fetches on navigation for large paginated queries.

No critical performance regressions. The app follows all Next.js best practices for a chart-heavy dashboard.
