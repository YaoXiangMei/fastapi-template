# ── Development ──────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies
	uv sync

.PHONY: dev
dev: ## Start API server (hot reload)
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker: ## Start Celery worker
	uv run celery -A app.worker.celery_app worker --loglevel=info

.PHONY: beat
beat: ## Start Celery beat
	uv run celery -A app.worker.celery_app beat --loglevel=info

# ── Database ────────────────────────────────────────────────

.PHONY: migrate
migrate: ## Run database migrations
	uv run alembic upgrade head

.PHONY: migrate-down
migrate-down: ## Rollback last migration
	uv run alembic downgrade -1

.PHONY: migrate-create
migrate-create: ## Create new migration (usage: make migrate-create msg="add users table")
	uv run alembic revision --autogenerate -m "$(msg)"

.PHONY: seed
seed: ## Run seed script (permissions + admin)
	uv run python -m app.scripts.seed

# ── Testing & Linting ───────────────────────────────────────

.PHONY: test
test: ## Run tests
	uv run pytest -v

.PHONY: lint
lint: ## Run linting (ruff check + format check + mypy)
	uv run ruff check app tests
	uv run ruff format --check app tests
	uv run mypy app

.PHONY: format
format: ## Auto-format code
	uv run ruff check --fix app tests
	uv run ruff format app tests

# ── Docker ──────────────────────────────────────────────────

.PHONY: docker-up
docker-up: ## Start all Docker services
	docker compose up -d --build

.PHONY: docker-down
docker-down: ## Stop all Docker services
	docker compose down

.PHONY: docker-logs
docker-logs: ## View Docker logs
	docker compose logs -f

.PHONY: docker-db-only
docker-db-only: ## Start only PostgreSQL + Redis
	docker compose up -d postgres redis

# ── Cleanup ─────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove __pycache__, .pytest_cache, .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

.PHONY: reset-db
reset-db: ## Drop and recreate test database
	dropdb --if-exists fastapi_template_test
	createdb fastapi_template_test
