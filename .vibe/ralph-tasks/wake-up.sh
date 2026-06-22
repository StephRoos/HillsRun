#!/bin/bash
# Ralph Tasks - Continuous Execution Loop (hardened)
# Usage: ./wake-up.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
TASKS_FILE="$SCRIPT_DIR/tasks.json"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
WAIT_SECONDS=60
MAX_STALL=3   # abort if no task completes after this many consecutive iterations

# Desktop notification (best effort, macOS / linux)
notify() {
  local msg="$1"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$msg\" with title \"Ralph Tasks — HillsRun\"" 2>/dev/null || true
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send "Ralph Tasks — HillsRun" "$msg" 2>/dev/null || true
  fi
  echo "🔔 $msg"
}

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 🤖 RALPH TASKS STARTING                    ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ Project: $PROJECT_DIR"
echo "║ Branch:  $(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"
echo "║ Tasks:   $TASKS_FILE"
echo "║ Stall guard: abort after $MAX_STALL iterations with no progress"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$PROJECT_DIR"

ITERATION=0
STALL=0
PREV_COMPLETED=-1

while true; do
  ITERATION=$((ITERATION + 1))

  PENDING=$(jq '[.tasks[] | select(.status == "pending")] | length' "$TASKS_FILE")
  IN_PROGRESS=$(jq '[.tasks[] | select(.status == "in_progress")] | length' "$TASKS_FILE")
  COMPLETED=$(jq '[.tasks[] | select(.status == "completed")] | length' "$TASKS_FILE")
  TOTAL=$(jq '.tasks | length' "$TASKS_FILE")

  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "📍 Iteration $ITERATION | Pending: $PENDING | In Progress: $IN_PROGRESS | Completed: $COMPLETED / $TOTAL"
  echo "═══════════════════════════════════════════════════════════════"

  # All done → push, notify, exit (finite batch, do not idle forever)
  if [ "$PENDING" -eq 0 ] && [ "$IN_PROGRESS" -eq 0 ]; then
    if [ "$TOTAL" -gt 0 ] && [ "$COMPLETED" -eq "$TOTAL" ]; then
      git push -q 2>/dev/null || true
      notify "✅ All $TOTAL tasks completed. Review the PR."
      echo "🎉 Done. Commits pushed. Review at: git log --oneline"
      exit 0
    fi
    echo ""
    echo "💤 No pending tasks. Waiting ${WAIT_SECONDS}s..."
    sleep "$WAIT_SECONDS"
    continue
  fi

  # Stall detection: completed count must advance over time
  if [ "$COMPLETED" -eq "$PREV_COMPLETED" ]; then
    STALL=$((STALL + 1))
  else
    STALL=0
  fi
  PREV_COMPLETED=$COMPLETED

  if [ "$STALL" -ge "$MAX_STALL" ]; then
    git push -q 2>/dev/null || true
    notify "⚠️ Stalled after $MAX_STALL iterations with no completion. Stopping."
    echo "🛑 Aborting: no task completed in $MAX_STALL iterations. See progress.txt."
    exit 1
  fi

  echo ""
  echo "🚀 Starting Claude agent..."
  echo ""

  OUTPUT=$(claude -p --dangerously-skip-permissions \
    "@$TASKS_FILE @$PROGRESS_FILE @$PROMPT_FILE" 2>&1 \
    | tee /dev/stderr) || true

  # Push after each iteration so committed work survives a crash/sleep
  git push -q 2>/dev/null || true

  sleep 2
done
