.PHONY: help build up down logs init-db backup sync sync-full sync-dry clean test

help: ## Show this help message
	@echo "Garmin Connect Sync - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

up: ## Start PostgreSQL service
	docker-compose up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 10
	@docker-compose ps postgres

down: ## Stop all services
	docker-compose down

logs: ## View PostgreSQL logs
	docker-compose logs -f postgres

init-db: ## Initialize database schema
	./scripts/init_db.sh

backup: ## Create database backup
	./scripts/backup_db.sh

sync: ## Run incremental sync
	docker-compose --profile sync run --rm garmin-sync

sync-full: ## Run full sync (last 90 days)
	docker-compose --profile sync run --rm garmin-sync --full

sync-dry: ## Dry run (show what would be synced)
	docker-compose --profile sync run --rm garmin-sync --dry-run

sync-daily: ## Sync only daily health data
	docker-compose --profile sync run --rm garmin-sync --categories daily_health

sync-activities: ## Sync only activities
	docker-compose --profile sync run --rm garmin-sync --categories activities

clean: ## Clean up logs and temporary files
	rm -f logs/*.log
	docker-compose down -v

test: ## Run tests (if implemented)
	python -m pytest tests/

install-deps: ## Install Python dependencies
	pip install -r requirements.txt

setup: build up init-db ## Complete initial setup
	@echo ""
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Authenticate with Garmin (see README.md)"
	@echo "  2. Run: make sync-dry"
	@echo "  3. Run: make sync-full"

status: ## Check sync status in database
	docker-compose exec postgres psql -U garmin -d garmin_connect -c "SELECT * FROM sync_state ORDER BY last_sync_timestamp DESC;"

psql: ## Connect to PostgreSQL
	docker-compose exec postgres psql -U garmin -d garmin_connect

.DEFAULT_GOAL := help
