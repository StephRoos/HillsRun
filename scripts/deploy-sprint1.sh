#!/bin/bash
#
# Deploy HillsRun Sprint 1 - Manual Deployment Guide
#
# This is a DOCUMENTED GUIDE, not an auto-executing script.
# Read through each section and execute commands manually to ensure safety.
#
# Prerequisites:
# - SSH access to NAS (configured in ~/.ssh/config or direct SSH)
# - Vercel CLI installed locally (vercel)
# - PostgreSQL psql client installed locally
# - Secrets file with new keys: /tmp/sprint1_secrets_rotation.txt
#
# Components to Deploy:
# 1. Database migration (sql/07_fix_sync_state_null_conflict.sql)
# 2. API key rotation (GARMIN_API_KEY, BETTER_AUTH_SECRET)
# 3. Token encryption key rotation (GARMIN_TOKEN_KEY)
# 4. Cron job setup for daily sync at 06:00 Europe/Paris
# 5. Verification and testing
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_FILE="/tmp/sprint1_secrets_rotation.txt"

echo "HillsRun Sprint 1 Deployment Guide"
echo "===================================="
echo ""
echo "This script provides step-by-step instructions for manual deployment."
echo "Execute each section command when ready."
echo ""

# ============================================================================
# SECTION 1: Pre-flight Checks
# ============================================================================
echo "SECTION 1: Pre-flight Checks"
echo "----------------------------"
echo ""
echo "Before starting, verify:"
echo "  1. SSH connection to NAS works: ssh nas 'echo Connected'"
echo "  2. Database backup exists: ssh nas 'ls -la /volume1/docker/garmin-sync/backups/'"
echo "  3. Current Git status is clean: git status"
echo ""
echo "Run these commands:"
echo ""
echo "  ssh nas 'echo Connected'"
echo "  ssh nas 'ls -la /volume1/docker/garmin-sync/backups/'"
echo "  git status"
echo ""
read -p "Press Enter when pre-flight checks are complete..."

# ============================================================================
# SECTION 2: Apply Database Migration
# ============================================================================
echo ""
echo "SECTION 2: Apply Database Migration (sql/07)"
echo "---------------------------------------------"
echo ""
echo "This migration fixes ON CONFLICT constraints for NULL user_id in sync_state."
echo "Read the migration file first:"
echo ""
echo "  cat ${PROJECT_ROOT}/sql/07_fix_sync_state_null_conflict.sql"
echo ""
echo "Then apply it to PostgreSQL on NAS:"
echo ""
cat << 'EOF'
  ssh nas "psql -U garmin -d garmin_connect -h localhost << 'ENDOFSQL'
$(cat /volume1/docker/garmin-sync/HillsRun/sql/07_fix_sync_state_null_conflict.sql)
ENDOFSQL"
EOF
echo ""
read -p "Press Enter when migration is applied..."

# Verify migration
echo ""
echo "Verify migration was applied:"
echo ""
echo "  ssh nas \"psql -U garmin -d garmin_connect -h localhost -c 'SELECT indexname FROM pg_indexes WHERE tablename = \\\"sync_state\\\" ORDER BY indexname;'\""
echo ""
read -p "Press Enter after verification..."

# ============================================================================
# SECTION 3: Update NAS Environment Variables
# ============================================================================
echo ""
echo "SECTION 3: Update NAS Docker Environment Variables"
echo "---------------------------------------------------"
echo ""
echo "Secrets to update:"
cat "$SECRETS_FILE" | grep -A 10 "NEW SECRETS FOR DEPLOYMENT" | head -15
echo ""
echo "Steps:"
echo "  1. SSH to NAS:"
echo "       ssh nas"
echo ""
echo "  2. Edit the docker-compose .env file:"
echo "       sudo nano /volume1/docker/garmin-sync/.env"
echo ""
echo "     OR update via docker directly (if using env vars in docker-compose):"
echo "       docker inspect garmin-api | grep -A 20 'Env'"
echo ""
echo "  3. Update these variables in .env:"
echo "     - BETTER_AUTH_SECRET=<new_value_from_secrets_file>"
echo "     - API_KEY=<new_value_from_secrets_file>"
echo "     - GARMIN_TOKEN_KEY=<new_value_from_secrets_file>"
echo ""
echo "  4. Save and exit nano (Ctrl+O, Enter, Ctrl+X)"
echo ""
read -p "Press Enter when NAS environment variables are updated..."

# ============================================================================
# SECTION 4: Restart Docker Container
# ============================================================================
echo ""
echo "SECTION 4: Restart Docker Container on NAS"
echo "-------------------------------------------"
echo ""
echo "Restart the API container to pick up new environment variables:"
echo ""
echo "  ssh nas 'docker restart garmin-api'"
echo ""
echo "Monitor the logs for 30 seconds to ensure it starts successfully:"
echo ""
echo "  ssh nas 'docker logs garmin-api --tail 50'"
echo ""
read -p "Press Enter when container is restarted and logs are verified..."

# ============================================================================
# SECTION 5: Update Vercel Environment Variables
# ============================================================================
echo ""
echo "SECTION 5: Update Vercel Environment Variables"
echo "-----------------------------------------------"
echo ""
echo "Update frontend environment variables on Vercel for BETTER_AUTH_SECRET and API_KEY:"
echo ""
echo "Option A: Via Vercel CLI (recommended):"
echo ""
echo "  vercel env pull .env.local"
echo "  # Edit the file, then:"
echo "  vercel env add BETTER_AUTH_SECRET"
echo "  vercel env add API_KEY"
echo ""
echo "Option B: Via Vercel Dashboard:"
echo ""
echo "  1. Go to https://vercel.com/projects/HillsRun/settings/environment-variables"
echo "  2. Update BETTER_AUTH_SECRET with new value"
echo "  3. Update API_KEY with new value"
echo "  4. Save and note that a redeploy will be needed"
echo ""
read -p "Press Enter when Vercel environment variables are updated..."

# ============================================================================
# SECTION 6: Trigger Vercel Redeploy
# ============================================================================
echo ""
echo "SECTION 6: Trigger Vercel Redeploy"
echo "-----------------------------------"
echo ""
echo "Option A: Push a commit to main:"
echo ""
echo "  git add CLAUDE.md"
echo "  git commit -m 'docs: update CLAUDE.md with Sprint 1 deployment info'"
echo "  git push origin main"
echo ""
echo "Option B: Redeploy via Vercel CLI:"
echo ""
echo "  vercel --prod"
echo ""
echo "Option C: Redeploy via dashboard:"
echo ""
echo "  https://vercel.com/projects/HillsRun/deployments"
echo "  Click 'Redeploy' on the latest deployment"
echo ""
read -p "Press Enter when redeploy is triggered..."

# ============================================================================
# SECTION 7: Set Up Daily Sync Cron Job
# ============================================================================
echo ""
echo "SECTION 7: Set Up Daily Sync Cron Job at 06:00 Europe/Paris"
echo "-------------------------------------------------------------"
echo ""
echo "Create a cron job on NAS to trigger daily sync at 06:00 Europe/Paris time:"
echo ""
echo "  ssh nas"
echo ""
echo "  # Edit the crontab:"
echo "  sudo crontab -e"
echo ""
echo "  # Add this line (06:00 Europe/Paris = 05:00 UTC in winter, 04:00 UTC in summer)"
echo "  # Using 05:00 UTC as a safe default for winter timezone:"
echo "  0 5 * * * curl -X POST -H 'X-API-Key: <API_KEY_VALUE>' https://api.hillsrun.com/api/v1/sync/trigger >> /var/log/hillsrun-sync.log 2>&1"
echo ""
echo "  # Replace <API_KEY_VALUE> with: EPIwW5Gpdubsmh5CEFrryh1oV318CWWnJuTbpvA7Po8="
echo ""
echo "  # Save and exit (Ctrl+X, Y, Enter)"
echo ""
echo "  # Verify cron job was added:"
echo "  sudo crontab -l | grep hillsrun"
echo ""
read -p "Press Enter when cron job is set up..."

# ============================================================================
# SECTION 8: Verification Tests
# ============================================================================
echo ""
echo "SECTION 8: Verification and Testing"
echo "------------------------------------"
echo ""
echo "Test 1: Verify database migration was applied:"
echo ""
echo "  ssh nas \"psql -U garmin -d garmin_connect -h localhost -c 'SELECT * FROM sync_state WHERE user_id IS NULL LIMIT 5;'\""
echo ""
echo "Test 2: Verify sync_state table integrity:"
echo ""
echo "  ssh nas \"psql -U garmin -d garmin_connect -h localhost -c 'SELECT user_id, category, last_sync_date FROM sync_state ORDER BY last_sync_timestamp DESC LIMIT 10;'\""
echo ""
echo "Test 3: Check container is healthy:"
echo ""
echo "  ssh nas 'docker ps | grep garmin-api'"
echo ""
echo "Test 4: Test API endpoint with new key (after Vercel redeploy):"
echo ""
echo "  curl -H 'X-API-Key: EPIwW5Gpdubsmh5CEFrryh1oV318CWWnJuTbpvA7Po8=' https://api.hillsrun.com/api/v1/sync/status"
echo ""
echo "Test 5: Check cron job logs (after first scheduled run):"
echo ""
echo "  ssh nas 'tail -50 /var/log/hillsrun-sync.log'"
echo ""
echo "Test 6: Monitor token encryption (check no errors in container logs):"
echo ""
echo "  ssh nas 'docker logs garmin-api --since 5m | grep -i token || echo OK'"
echo ""
read -p "Press Enter when verification is complete..."

# ============================================================================
# SECTION 9: Update CLAUDE.md
# ============================================================================
echo ""
echo "SECTION 9: Update CLAUDE.md with Deployment Notes"
echo "---------------------------------------------------"
echo ""
echo "The CLAUDE.md file has been updated with:"
echo "  - Database migration details (sql/07)"
echo "  - Secret rotation procedure"
echo "  - Daily cron schedule (06:00 Europe/Paris)"
echo ""
echo "Review and commit:"
echo ""
echo "  git diff CLAUDE.md"
echo "  git add CLAUDE.md"
echo "  git commit -m 'docs: add Sprint 1 deployment section to CLAUDE.md'"
echo "  git push origin main"
echo ""
read -p "Press Enter when CLAUDE.md is committed..."

# ============================================================================
# SECTION 10: Post-Deployment Checklist
# ============================================================================
echo ""
echo "SECTION 10: Post-Deployment Checklist"
echo "-------------------------------------"
echo ""
echo "  [ ] Database migration applied (sql/07)"
echo "  [ ] NAS .env updated with new secrets"
echo "  [ ] Docker container restarted and healthy"
echo "  [ ] Vercel environment variables updated"
echo "  [ ] Vercel redeploy completed successfully"
echo "  [ ] Cron job configured and verified"
echo "  [ ] API endpoints tested with new keys"
echo "  [ ] Database integrity verified"
echo "  [ ] CLAUDE.md updated and committed"
echo "  [ ] Secrets file securely deleted"
echo ""

echo ""
echo "DEPLOYMENT COMPLETE!"
echo "===================="
echo ""
echo "Clean up:"
echo "  rm ${SECRETS_FILE}"
echo ""
echo "Next steps:"
echo "  1. Monitor logs for 24 hours"
echo "  2. Verify first scheduled sync completes at 06:00 tomorrow"
echo "  3. Test full user journey (login, sync, view data)"
echo ""
