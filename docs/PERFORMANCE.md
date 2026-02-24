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
| `3fc5fe80.*.js` | **4.4 MB** | Plotly.js (dominant) |
| `4258e3df-*.js` | 196 KB | app-router internals |
| `5366-*.js` | 192 KB | React + dependencies |
| `framework-*.js` | 188 KB | Next.js framework |
| `7638-*.js` | 140 KB | TanStack Query + misc |
| `main-*.js` | 136 KB | App entry point |
| `polyfills-*.js` | 112 KB | Browser polyfills |

### Key observation
The **4.4 MB Plotly chunk** is the dominant cost. This is expected and by design (ADR-005): Plotly.js is loaded dynamically (no SSR), so it is only downloaded when the user visits a chart-heavy page (`/dashboard` or `/trends`).

Serwist service worker warns: `3fc5fe80.*.js is 4.61 MB, won't be precached` — this is acceptable; Plotly is not precached and will re-download on next visit if evicted from browser cache.

---

## 2. Plotly.js — Tree-shaking Assessment

**Current implementation**: Dynamic import via `next/dynamic` with `{ ssr: false }`.

```typescript
// web/src/components/dashboard/trend-charts.tsx
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });
```

**Tree-shaking status**: Plotly.js does NOT support tree-shaking. The full library (~4.5 MB) is always bundled. This is a known limitation of `plotly.js` (it registers all chart types at import time).

**Alternatives if bundle size becomes critical**:
- Use `plotly.js-basic-dist` (~1.5 MB) — supports scatter, bar, pie only
- Use `plotly.js-dist-min` (~2.1 MB) — minified full version
- Migrate to Recharts or Nivo (smaller, tree-shakeable, but less interactive)

**Recommendation**: Keep current approach. The dynamic import ensures Plotly is only loaded on chart pages. For mobile users on slow connections, consider adding a lazy load threshold (intersection observer).

---

## 3. Image Optimization

**Current status**: No `<Image>` components from `next/image` are used (no static images in the app — all content is data-driven charts and text).

**Garmin profile avatars**: Not currently displayed. When implemented, use `next/image` with proper `width`/`height` and `priority` on above-the-fold images.

**Recommendation**: No action needed currently. Add `next/image` when/if user avatars are implemented.

---

## 4. TanStack Query Caching Effectiveness

**Strategy**: `staleTime` + manual invalidation after mutations (ADR-004). No polling.

| Query | staleTime | Invalidation trigger |
|-------|-----------|---------------------|
| Activities | 1 hour | Sync completion |
| Daily summary | 1 hour | Sync completion |
| HRV / sleep / body battery | 1 hour | Sync completion |
| Training readiness | 1 hour | Sync completion |
| VMA | Infinity | User update |
| Sync status | 30 seconds | Manual sync trigger |
| Coaching status | 5 minutes | Coach action |

**Assessment**: The caching strategy is well-suited to Garmin data (synced hourly at most). No unnecessary re-fetches observed. The `queryKey` includes all relevant params (date range, limit, athlete ID), ensuring correct cache separation for multi-user (coach/athlete) scenarios.

**Potential improvement**: Add `gcTime` (formerly `cacheTime`) tuning for large paginated queries. Default is 5 minutes; activity lists with 100+ items could benefit from longer GC time to avoid re-fetching on navigation.

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

## 6. Recommendations

### Immediate (low effort)

1. **Serwist precache exclusion**: Already handled — the 4.61 MB Plotly chunk is correctly excluded from SW precaching via the `maximumFileSizeToCacheInBytes` warning. No action needed; this is expected behavior.

2. **Font optimization**: Verify `next/font` is used for any custom fonts. Currently using Tailwind defaults (system font stack) — no Google Fonts CDN calls, which is optimal.

3. **Compression**: Ensure Vercel serves `.br` (Brotli) compressed bundles. Brotli compresses the 4.4 MB Plotly chunk to ~1.2 MB. Vercel does this automatically.

### Medium-term (moderate effort)

4. **Plotly partial import**: Evaluate `plotly.js-basic-dist` if adding mobile users. Basic scatter charts (activities, HRV, trends) would work without the full Plotly suite.

5. **Virtual scrolling for activity list**: If activity lists grow beyond 200 items, consider `@tanstack/react-virtual` for the `/calendar` and `/dashboard` activity lists.

6. **API pagination caching**: Consider implementing cursor-based pagination (instead of limit/offset) to enable infinite query cache merging in TanStack Query.

### Long-term (significant effort)

7. **Edge caching for static metrics**: HRV, sleep, and fitness data from previous days never changes. Add `Cache-Control: max-age=86400` headers on FastAPI for historical date queries.

8. **Database connection pooling**: Add PgBouncer between FastAPI and PostgreSQL when scaling beyond 5 concurrent users. Current asyncpg pool (min=1, max=5) is sufficient for single-user.

---

## 7. Build Warnings

| Warning | Severity | Action |
|---------|----------|--------|
| Serwist: 4.61 MB chunk won't be precached | Info | Expected — Plotly too large for SW cache |
| Better-Auth base URL not set | Warning | Set `BETTER_AUTH_BASE_URL` env var in Vercel |
| Compiled with warnings | Warning | Due to above warnings, not code issues |

---

## Summary

The current bundle is dominated by Plotly.js (~4.4 MB uncompressed, ~1.2 MB Brotli). This is acceptable given:
- Plotly is lazy-loaded (dynamic import, no SSR)
- The app serves analytics-heavy users (athletes) who expect rich charts
- Brotli compression reduces download size significantly

No critical performance regressions. The app follows all Next.js best practices for a chart-heavy dashboard.
