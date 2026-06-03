# HillsRun frontend — Next.js 16 standalone, for Coolify on UM880.
# Build context = web/ (set in docker-compose.coolify.yml).

# ─── Stage 1: Install dependencies ─────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app

# pnpm pinned (lockfileVersion 9.0) — never @latest in a Dockerfile.
RUN corepack enable && corepack prepare pnpm@10.33.2 --activate

# prisma.config.ts + schema are needed because package.json's `postinstall`
# runs `prisma generate` during install (generator output = ../src/generated/prisma).
COPY package.json pnpm-lock.yaml prisma.config.ts ./
COPY prisma ./prisma

RUN pnpm install --frozen-lockfile

# ─── Stage 2: Build the application ─────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@10.33.2 --activate

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* must be present at build time — Next.js inlines them into the
# client bundle. Passed via --build-arg from the compose file.
ARG NEXT_PUBLIC_BETTER_AUTH_URL
ENV NEXT_PUBLIC_BETTER_AUTH_URL=$NEXT_PUBLIC_BETTER_AUTH_URL

# Regenerate the Prisma client into src/generated/prisma (host source has no
# generated dir — it is gitignored — so the deps-stage copy is not carried over).
RUN pnpm exec prisma generate

# Build Next.js (output: "standalone") — also emits the Serwist service worker.
RUN pnpm build

# ─── Stage 3: Production runtime ─────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
# Next standalone binds to HOSTNAME — must be 0.0.0.0 inside Docker.
ENV HOSTNAME=0.0.0.0

# Non-root runtime user.
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Standalone server + static assets + public (includes the generated sw.js).
# No Prisma CLI / migrate here: the database is pre-seeded from the Neon dump,
# and the runtime client + query engine are traced into .next/standalone.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/ >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
