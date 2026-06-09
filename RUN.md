# RUN — Autonomous Ralph loop (road marathon + adaptive coach)

Single run **A + D** (11 tasks) on branch `feat/road-marathon-engine`.
Sprint A = road-marathon engine + generate my plan. Sprint D = adaptive coach.

## 0. Prerequisites

```bash
jq --version       # required by the loop — else: brew install jq
claude --version   # Claude CLI
uv --version       # Python backend manager
```

DB env vars needed by task #7 (seed + generate my plan), as usual:
`POSTGRES_HOST/PORT/DB/USER/PASSWORD`, `GARMIN_TOKEN_KEY` (in env or project `.env`).

## 1. Get the branch

```bash
cd <path>/HillsRun
git fetch origin
git checkout feat/road-marathon-engine
git pull
jq '.tasks | length' .claude/ralph-tasks/tasks.json   # expect 11
```

## 2. Launch the loop

```bash
sh .claude/ralph-tasks/wake-up.sh
```

Picks task 1 → code → `uv run pytest` + `ruff` → commit → next… through task 11.
Pushes after each lot, stops itself if stalled (3 iterations with no progress), and
notifies on completion. **Ctrl+C** to stop; relaunch to resume at the next unfinished task.

## 3. Tasks

| # | Lot | Nature |
|---|---|---|
| 1-6 | Road engine (discipline, VMA paces, long run, catalog, wiring, DB+API+PR) | code |
| 7 | Seed my profile + generate my plan → `specs/mon-plan-marathon.md` | code |
| 8 | D1 — daily HRV coach (GO/EASE/REST verdict) | non-destructive |
| 9 | D2 — AI reasoning layer | non-destructive |
| 10 | D3 — planned↔actual reconciliation | read-only |
| 11 | D4 — weekly adjustment | propose-only |

## 4. On waking

```bash
git log --oneline -15
cat .claude/ralph-tasks/progress.txt
cat specs/mon-plan-marathon.md
gh pr view --web
```

## 5. Manual post-merge (the agent does NOT touch prod)

Apply migrations by hand to Neon + NAS replica:
```bash
psql "$NEON_URL" -f sql/11_road_marathon.sql
psql "$NEON_URL" -f sql/12_daily_recommendations.sql
```

Specs: `specs/02-road-marathon-adaptation.md`, `specs/03-adaptive-coach.md`.
