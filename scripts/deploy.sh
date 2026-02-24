#!/bin/bash
#
# HillsRun Deployment Guide
# Usage: ./scripts/deploy.sh [frontend|backend|all]
#
# This is a DOCUMENTED GUIDE, not an auto-executing script.
# Read each section and run the commands manually as needed.
#
# Architecture:
#   - Frontend: Next.js app deployed on Vercel (auto-deploy via git push)
#   - Backend:  FastAPI in Docker container on NAS (ARM64, manual deploy)
#   - Tunnel:   Cloudflare Tunnel for remote access (no VPN needed)
#
# Prerequisites:
#   - SSH access to NAS configured in ~/.ssh/config: Host nas
#   - Git remote: origin → GitHub (Vercel watches this)
#   - Docker image: garmin-api:arm64 on NAS
#

set -euo pipefail

COMPONENT="${1:-all}"
NAS_PROJECT_DIR="/volume1/docker/garmin-sync/HillsRun"
DOCKER_CONTAINER="garmin-api"
DOCKER_IMAGE="garmin-api:arm64"
DOCKERFILE="Dockerfile.api"
API_BASE="https://api.hillsrun.com"
FRONTEND_BASE="https://hillsrun.com"

# ============================================================================
# FRONTEND DEPLOYMENT (Vercel — automatic via git push)
# ============================================================================
deploy_frontend() {
  echo "=== FRONTEND DEPLOYMENT ==="
  echo ""
  echo "The frontend deploys automatically when you push to main."
  echo "Vercel is configured to watch the 'web/' subdirectory."
  echo ""
  echo "Steps:"
  echo ""
  echo "  1. Ensure all changes are committed:"
  echo "       git status"
  echo "       git add <files>"
  echo "       git commit -m 'feat: ...'   # conventional commit format"
  echo ""
  echo "  2. Push to trigger auto-deploy:"
  echo "       git push origin main"
  echo ""
  echo "  3. Monitor deployment:"
  echo "       # Visit https://vercel.com/projects/HillsRun/deployments"
  echo "       # Or use Vercel CLI:"
  echo "       vercel logs --follow"
  echo ""
  echo "  4. Verify live site:"
  echo "       curl -I ${FRONTEND_BASE}"
  echo ""
  echo "Notes:"
  echo "  - Vercel root directory is 'web/' (configured in vercel.json or project settings)"
  echo "  - Build command: pnpm build"
  echo "  - Env vars must be set in Vercel dashboard (BETTER_AUTH_SECRET, GARMIN_API_KEY, etc.)"
  echo "  - Preview deployments are created for pull requests automatically"
  echo ""
}

# ============================================================================
# BACKEND HOT-PATCH (apply file changes without full rebuild)
# ============================================================================
deploy_backend_hotpatch() {
  echo "=== BACKEND HOT-PATCH ==="
  echo ""
  echo "Use hot-patch when only Python source files changed (no new dependencies)."
  echo "This avoids a full Docker rebuild (~5-10 min saved)."
  echo ""
  echo "Steps:"
  echo ""
  echo "  1. SSH to NAS and pull latest changes:"
  echo "       ssh nas"
  echo "       cd ${NAS_PROJECT_DIR}"
  echo "       git pull origin main"
  echo ""
  echo "  2. Restart the container to pick up file changes:"
  echo "       docker restart ${DOCKER_CONTAINER}"
  echo ""
  echo "  3. Check logs to confirm successful startup:"
  echo "       docker logs ${DOCKER_CONTAINER} --tail 50 --follow"
  echo "       # Wait for: 'API started, user_id=...'"
  echo "       # Ctrl+C to exit log follow"
  echo ""
  echo "Alternatively, copy a single file without a git pull:"
  echo ""
  echo "  # Example: patch src/api/middleware.py"
  echo "  cat src/api/middleware.py | ssh nas \\"
  echo "    'cat > /tmp/middleware.py && docker cp /tmp/middleware.py ${DOCKER_CONTAINER}:/app/src/api/middleware.py'"
  echo "  ssh nas 'docker restart ${DOCKER_CONTAINER}'"
  echo ""
}

# ============================================================================
# BACKEND FULL REBUILD (when dependencies or Dockerfile change)
# ============================================================================
deploy_backend_full() {
  echo "=== BACKEND FULL REBUILD ==="
  echo ""
  echo "Use full rebuild when pyproject.toml, Dockerfile, or system deps changed."
  echo ""
  echo "Steps:"
  echo ""
  echo "  1. SSH to NAS:"
  echo "       ssh nas"
  echo ""
  echo "  2. Pull latest code:"
  echo "       cd ${NAS_PROJECT_DIR}"
  echo "       git pull origin main"
  echo ""
  echo "  3. Build new Docker image (ARM64 cross-compile if needed):"
  echo "       docker build -f ${DOCKERFILE} -t ${DOCKER_IMAGE} ."
  echo "       # This can take 5-15 minutes on NAS ARM64"
  echo ""
  echo "  4. Stop and restart container with new image:"
  echo "       docker stop ${DOCKER_CONTAINER}"
  echo "       docker rm ${DOCKER_CONTAINER}"
  echo "       # Start using docker-compose (preserves env vars and volumes):"
  echo "       docker-compose up -d ${DOCKER_CONTAINER}"
  echo "       # OR start manually with the same flags as the current container:"
  echo "       docker inspect ${DOCKER_CONTAINER} --format '{{.Config.Cmd}}'"
  echo ""
  echo "  5. Verify container started:"
  echo "       docker ps | grep ${DOCKER_CONTAINER}"
  echo "       docker logs ${DOCKER_CONTAINER} --tail 50"
  echo ""
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================
health_check() {
  echo "=== HEALTH CHECKS ==="
  echo ""
  echo "Run after any deployment to verify the system is working."
  echo ""
  echo "1. Backend health endpoint:"
  echo "     curl -s ${API_BASE}/health | python3 -m json.tool"
  echo "     # Expected: { \"status\": \"ok\", ... }"
  echo ""
  echo "2. API authentication check (requires API key):"
  echo "     # Replace <API_KEY> with the value from your .env"
  echo "     curl -s -H 'X-API-Key: <API_KEY>' ${API_BASE}/api/v1/sync/status | python3 -m json.tool"
  echo "     # Expected: { \"data\": [...] }"
  echo ""
  echo "3. Cache-Control headers verification:"
  echo "     # Historical date (should return Cache-Control: public, max-age=86400)"
  echo "     curl -sI -H 'X-API-Key: <API_KEY>' '${API_BASE}/api/v1/daily/summary?end_date=2025-01-01' | grep cache"
  echo ""
  echo "     # Today's date (should return Cache-Control: private, max-age=300)"
  echo "     curl -sI -H 'X-API-Key: <API_KEY>' '${API_BASE}/api/v1/daily/summary' | grep cache"
  echo ""
  echo "     # Sync endpoint (should return Cache-Control: no-store)"
  echo "     curl -sI -H 'X-API-Key: <API_KEY>' '${API_BASE}/api/v1/sync/status' | grep cache"
  echo ""
  echo "4. Frontend health check:"
  echo "     curl -I ${FRONTEND_BASE}"
  echo "     # Expected: HTTP/2 200"
  echo ""
  echo "5. Container status on NAS:"
  echo "     ssh nas 'docker ps | grep ${DOCKER_CONTAINER}'"
  echo "     ssh nas 'docker stats ${DOCKER_CONTAINER} --no-stream'"
  echo ""
}

# ============================================================================
# ROLLBACK INSTRUCTIONS
# ============================================================================
rollback() {
  echo "=== ROLLBACK INSTRUCTIONS ==="
  echo ""
  echo "--- Frontend Rollback (Vercel) ---"
  echo ""
  echo "  Option A: Via Vercel Dashboard (fastest):"
  echo "    1. Go to https://vercel.com/projects/HillsRun/deployments"
  echo "    2. Find the last known-good deployment"
  echo "    3. Click the three-dot menu → 'Redeploy'"
  echo ""
  echo "  Option B: Via git revert:"
  echo "    git revert HEAD"
  echo "    git push origin main"
  echo "    # Vercel auto-deploys the reverted commit"
  echo ""
  echo "--- Backend Rollback (Docker on NAS) ---"
  echo ""
  echo "  Option A: Revert code and hot-patch:"
  echo "    ssh nas"
  echo "    cd ${NAS_PROJECT_DIR}"
  echo "    git log --oneline -10          # find last good commit"
  echo "    git checkout <good-commit-hash> -- src/"
  echo "    docker restart ${DOCKER_CONTAINER}"
  echo ""
  echo "  Option B: Use a previous Docker image (if tagged):"
  echo "    ssh nas"
  echo "    docker images | grep garmin-api   # list available images"
  echo "    docker stop ${DOCKER_CONTAINER}"
  echo "    docker rm ${DOCKER_CONTAINER}"
  echo "    # Start with the previous image tag:"
  echo "    docker run -d --name ${DOCKER_CONTAINER} [original flags] garmin-api:previous"
  echo ""
  echo "  Option C: Full git reset on NAS:"
  echo "    ssh nas"
  echo "    cd ${NAS_PROJECT_DIR}"
  echo "    git fetch origin"
  echo "    git reset --hard origin/main~1   # go back one commit on main"
  echo "    docker restart ${DOCKER_CONTAINER}"
  echo ""
  echo "  Verify rollback was successful:"
  echo "    ssh nas 'docker logs ${DOCKER_CONTAINER} --tail 20'"
  echo "    curl -s ${API_BASE}/health | python3 -m json.tool"
  echo ""
}

# ============================================================================
# SMOKE TEST (runs scripts/smoke-test.sh against live API)
# ============================================================================
run_smoke_test() {
  echo "=== SMOKE TEST ==="
  echo ""
  echo "Runs post-deploy smoke tests against the live API."
  echo "Requires API_URL and API_KEY (or env vars GARMIN_API_URL / GARMIN_API_KEY)."
  echo ""
  echo "Usage:"
  echo "  ./scripts/smoke-test.sh [API_URL] [API_KEY]"
  echo ""
  echo "Example:"
  echo "  ./scripts/smoke-test.sh ${API_BASE} '<your-api-key>'"
  echo ""
  echo "To run now (if env vars are set):"
  echo "  GARMIN_API_URL=${API_BASE} GARMIN_API_KEY=<key> ./scripts/smoke-test.sh"
  echo ""
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -n "${2:-}" ]]; then
    "${SCRIPT_DIR}/smoke-test.sh" "${1:-${API_BASE}}" "${2}"
  elif [[ -n "${GARMIN_API_KEY:-}" ]]; then
    "${SCRIPT_DIR}/smoke-test.sh" "${GARMIN_API_URL:-${API_BASE}}" "${GARMIN_API_KEY}"
  else
    echo "Note: no API key provided — only the public /health endpoint will be tested."
    "${SCRIPT_DIR}/smoke-test.sh" "${1:-${API_BASE}}"
  fi
}

# ============================================================================
# VERIFY (checks frontend + backend health endpoints)
# ============================================================================
verify() {
  echo "=== DEPLOYMENT VERIFICATION ==="
  echo ""
  echo "Checking frontend health..."
  FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_BASE}" 2>/dev/null || echo "000")
  if [[ "${FRONTEND_STATUS}" == "200" ]]; then
    echo "  PASS  Frontend ${FRONTEND_BASE} → HTTP ${FRONTEND_STATUS}"
  else
    echo "  FAIL  Frontend ${FRONTEND_BASE} → HTTP ${FRONTEND_STATUS}"
  fi
  echo ""
  echo "Checking frontend health API..."
  FRONTEND_HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_BASE}/api/health" 2>/dev/null || echo "000")
  if [[ "${FRONTEND_HEALTH_STATUS}" == "200" ]]; then
    echo "  PASS  ${FRONTEND_BASE}/api/health → HTTP ${FRONTEND_HEALTH_STATUS}"
  else
    echo "  FAIL  ${FRONTEND_BASE}/api/health → HTTP ${FRONTEND_HEALTH_STATUS}"
  fi
  echo ""
  echo "Checking backend health..."
  BACKEND_HEALTH=$(curl -s "${API_BASE}/health" 2>/dev/null || echo '{"status":"unreachable"}')
  BACKEND_STATUS=$(echo "${BACKEND_HEALTH}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null || echo "?")
  if [[ "${BACKEND_STATUS}" == "ok" ]]; then
    echo "  PASS  Backend ${API_BASE}/health → status=${BACKEND_STATUS}"
    echo "        ${BACKEND_HEALTH}"
  else
    echo "  FAIL  Backend ${API_BASE}/health → status=${BACKEND_STATUS}"
    echo "        ${BACKEND_HEALTH}"
  fi
  echo ""
}

# ============================================================================
# STATUS (show current deployment state)
# ============================================================================
deployment_status() {
  echo "=== DEPLOYMENT STATUS ==="
  echo ""
  echo "--- Backend (${API_BASE}) ---"
  echo ""
  echo "  Health endpoint:"
  curl -s "${API_BASE}/health" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  (unreachable)"
  echo ""
  echo "  Container status on NAS:"
  echo "    ssh nas 'docker ps --filter name=${DOCKER_CONTAINER} --format \"table {{.Status}}\\t{{.Ports}}\\t{{.Names}}\"'"
  echo ""
  echo "  Container logs (last 20 lines):"
  echo "    ssh nas 'docker logs ${DOCKER_CONTAINER} --tail 20'"
  echo ""
  echo "--- Frontend (${FRONTEND_BASE}) ---"
  echo ""
  FRONTEND_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_BASE}" 2>/dev/null || echo "000")
  echo "  ${FRONTEND_BASE} → HTTP ${FRONTEND_CODE}"
  echo ""
  echo "  For Vercel deployment status:"
  echo "    https://vercel.com/projects/HillsRun/deployments"
  echo ""
}

# ============================================================================
# MAIN DISPATCH
# ============================================================================
case "$COMPONENT" in
  frontend)
    deploy_frontend
    ;;
  backend)
    echo "Select backend deploy type:"
    echo "  ./scripts/deploy.sh backend-hotpatch   (file changes only)"
    echo "  ./scripts/deploy.sh backend-full       (deps or Dockerfile changed)"
    ;;
  backend-hotpatch)
    deploy_backend_hotpatch
    ;;
  backend-full)
    deploy_backend_full
    ;;
  health)
    health_check
    ;;
  smoke-test)
    run_smoke_test "$@"
    ;;
  verify)
    verify
    ;;
  status)
    deployment_status
    ;;
  rollback)
    rollback
    ;;
  all)
    deploy_frontend
    echo ""
    deploy_backend_hotpatch
    echo ""
    health_check
    ;;
  *)
    echo "Usage: $0 [frontend|backend|backend-hotpatch|backend-full|health|smoke-test|verify|status|rollback|all]"
    echo ""
    echo "Commands:"
    echo "  frontend          Show frontend deploy steps (Vercel auto-deploy via git push)"
    echo "  backend           Show backend deploy type selection"
    echo "  backend-hotpatch  Show hot-patch steps (no Docker rebuild)"
    echo "  backend-full      Show full rebuild steps (new deps or Dockerfile)"
    echo "  health            Show post-deploy health check commands"
    echo "  smoke-test        Run smoke-test.sh against live API"
    echo "  verify            Check frontend + backend health endpoints"
    echo "  status            Show current deployment state"
    echo "  rollback          Show rollback instructions"
    echo "  all               Show all steps in sequence (default)"
    exit 1
    ;;
esac
