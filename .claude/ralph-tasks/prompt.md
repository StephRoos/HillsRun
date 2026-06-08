# Ralph Tasks Agent Instructions — HillsRun road-marathon engine (Python/uv)

## Your Task

You are an autonomous AI coding agent working in the HillsRun repo. Each iteration
you implement ONE task from the queue. The authoritative spec is
`specs/02-road-marathon-adaptation.md` — read the section a task points to before
coding. Every decision is already pinned there; do not invent new behaviour.

## Execution Sequence

1. **Read Task Queue**
   - Read tasks.json. Take the first `status: "pending"` task (lowest id).
   - If a task is `in_progress`, continue that one.
   - If none pending/in_progress, output `<no-tasks>` and stop.

2. **Mark In Progress** (jq atomic):
   ```bash
   jq --argjson id TASK_ID '.tasks = [.tasks[] | if .id == $id then .status = "in_progress" else . end]' tasks.json > tmp.json && mv tmp.json tasks.json
   ```
   (tasks.json lives in .claude/ralph-tasks/)

3. **Implement**
   - Read `.claude/ralph-tasks/progress.txt` for prior learnings.
   - Read the referenced section of `specs/02-road-marathon-adaptation.md`.
   - Read the target source files before editing (line numbers may have drifted).
   - Make MINIMAL, surgical changes. New road logic must be gated on
     `discipline == 'road'` / `is_road_marathon` — never break trail behaviour.

4. **Verify (Python / uv — NOT pnpm)**
   ```bash
   uv run ruff check src/ && uv run ruff format src/
   uv run pytest tests/
   ```
   Fix everything before committing. NEVER commit red. Existing trail tests must
   stay green.

5. **Commit** (stay on branch `feat/road-marathon-engine`):
   ```bash
   git add -A && git commit -m "feat(training): #<id> - <lot summary>"
   ```

6. **Mark Completed** (jq atomic):
   ```bash
   jq --argjson id TASK_ID --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     '.tasks = [.tasks[] | if .id == $id then .status = "completed" | .completedAt = $date else . end]' \
     tasks.json > tmp.json && mv tmp.json tasks.json
   ```

7. **Log Learnings** — append to `.claude/ralph-tasks/progress.txt`:
   ```
   ## <date> - Task #<id>: <desc>
   - What was implemented / files changed
   - Learnings / gotchas (e.g. real signatures, pace formula edge cases)
   ---
   ```

## Stop Condition
No pending/in_progress task → output `<no-tasks>`.

## Critical Rules
- 🛑 ONE task per iteration. NEVER skip verification. NEVER commit failing tests.
- 🛑 Python project: use `uv run pytest` / `uv run ruff` — NEVER pnpm/npm here.
- 🛑 Do NOT push to `main`. Stay on `feat/road-marathon-engine`.
- ✅ Spec `specs/02-road-marathon-adaptation.md` is the source of truth.
- ✅ Mark in_progress before, completed after, log learnings, jq for JSON.
- ✅ Last task (#6) opens the PR after the e2e acceptance test is green.
