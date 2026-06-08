#!/bin/bash
# Ralph Tasks - Continuous Execution Loop
# Usage: ./wake-up.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
TASKS_FILE="$SCRIPT_DIR/tasks.json"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
WAIT_SECONDS=60

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 🤖 RALPH TASKS STARTING                    ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ Project: $PROJECT_DIR"
echo "║ Tasks file: $TASKS_FILE"
echo "║ Wait interval: ${WAIT_SECONDS}s when no tasks"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$PROJECT_DIR"

ITERATION=0

while true; do
  ITERATION=$((ITERATION + 1))

  # Get pending tasks count
  PENDING=$(jq '[.tasks[] | select(.status == "pending")] | length' "$TASKS_FILE")
  IN_PROGRESS=$(jq '[.tasks[] | select(.status == "in_progress")] | length' "$TASKS_FILE")
  COMPLETED=$(jq '[.tasks[] | select(.status == "completed")] | length' "$TASKS_FILE")
  TOTAL=$(jq '.tasks | length' "$TASKS_FILE")

  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "📍 Iteration $ITERATION | Pending: $PENDING | In Progress: $IN_PROGRESS | Completed: $COMPLETED / $TOTAL"
  echo "═══════════════════════════════════════════════════════════════"

  if [ "$PENDING" -eq 0 ] && [ "$IN_PROGRESS" -eq 0 ]; then
    echo ""
    echo "💤 No pending tasks. Waiting ${WAIT_SECONDS} seconds..."
    echo "   (Add tasks with: /ralph-tasks add \"your task\")"
    sleep "$WAIT_SECONDS"
    continue
  fi

  # Run Claude with the prompt
  echo ""
  echo "🚀 Starting Claude agent..."
  echo ""

  OUTPUT=$(claude -p --dangerously-skip-permissions \
    "@$TASKS_FILE @$PROGRESS_FILE @$PROMPT_FILE" 2>&1 \
    | tee /dev/stderr) || true

  # Brief pause between iterations
  sleep 2
done
