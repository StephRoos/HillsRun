# HillsRun Web — Trail Running Dashboard

Next.js frontend for HillsRun. Consumes the FastAPI backend to display trail-focused Garmin data.

## Stack

- **Next.js 16** (App Router, Turbopack)
- **Better-Auth** (email/password auth)
- **Prisma 7** (auth tables, PG driver adapter)
- **TanStack Query** (data fetching)
- **shadcn/ui** + Tailwind CSS v4
- **Plotly.js** (charts)

## Setup

```bash
pnpm install
pnpm prisma generate
```

Create `.env.local`:

```env
DATABASE_URL="postgresql://garmin:xxx@localhost:15432/garmin_connect"
NEXT_PUBLIC_GARMIN_API_URL="https://api.hillsrun.com"
GARMIN_API_KEY="your-api-key"
BETTER_AUTH_SECRET="generate-a-real-secret"
BETTER_AUTH_URL="http://localhost:3000"
NEXT_PUBLIC_BETTER_AUTH_URL="http://localhost:3000"
```

## Development

```bash
pnpm dev
```

If database is remote (via Cloudflare Tunnel):

```bash
# Start TCP proxy for PostgreSQL
cloudflared access tcp --hostname db.hillsrun.com --url localhost:15432
```

## Project Structure

```
src/
├── app/
│   ├── page.tsx                    # Landing page
│   ├── (auth)/                     # Login, signup
│   ├── (dashboard)/                # Protected pages
│   │   ├── dashboard/page.tsx      # Main dashboard
│   │   ├── activity/[id]/page.tsx  # Activity detail
│   │   ├── trends/page.tsx         # Trends charts
│   │   └── settings/page.tsx       # Settings
│   └── api/
│       ├── auth/[...all]/          # Better-Auth handler
│       └── garmin/[...path]/       # Proxy to FastAPI
├── components/
│   ├── ui/                         # shadcn/ui components
│   ├── dashboard/                  # Sidebar, nav, summary cards
│   ├── activity/                   # Activity cards, metrics, splits
│   └── charts/                     # Plotly charts
├── hooks/                          # TanStack Query hooks
├── lib/                            # Auth, Prisma, API client, utils
└── types/                          # TypeScript types
```

## Architecture

- **API Key security**: `GARMIN_API_KEY` is server-side only. Frontend calls `/api/garmin/*` proxy which adds the key.
- **Auth tables**: Managed by Prisma. Garmin tables are NOT in the Prisma schema to prevent `db push` from dropping them.
- **DB access**: Via `cloudflared access tcp` tunnel for remote development.
