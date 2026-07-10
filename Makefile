-include .env
export

COMPOSE := docker compose -f docker-compose.yml
COMPOSE_TEST := docker compose -p dsa-test -f docker-compose.test.yml
BACKEND_DIR := backend

POSTGRES_USER ?= dsa
POSTGRES_DB ?= dead_simple_analytics
BACKUP_DIR := backups/db

DOMAIN ?=
USERNAME ?= admin

.DEFAULT_GOAL := help

.PHONY: help docker-check up down status logs sync lint format test test-unit ci test-up test-down db install

help:
	@echo "Dead Simple Analytics - available targets:"
	@echo ""
	@echo "  make up              Start Postgres + API (port $${DSA_HOST_PORT:-8082})"
	@echo "  make down            Stop stack"
	@echo "  make status          Show service status"
	@echo "  make logs            Tail service logs"
	@echo ""
	@echo "  make install         Production install as current user (DOMAIN=...)"
	@echo ""
	@echo "  make sync            Install/update backend Python deps (uv)"
	@echo "  make lint            Run backend ruff lint"
	@echo "  make format          Run backend ruff format + fix"
	@echo ""
	@echo "  make test            Run backend tests (unit+integration, 100% coverage gate)"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make ci              lint + test"
	@echo "  make test-up         Start test Postgres on :5434"
	@echo "  make test-down       Stop test Postgres"
	@echo ""
	@echo "  make db migrate      Apply Alembic migrations"
	@echo "  make db backup       Dump database to $(BACKUP_DIR)/"
	@echo ""

docker-check:
	@docker info >/dev/null 2>&1 || (echo "Docker daemon is not running. Start Docker and retry." && exit 1)

up: docker-check
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

status: docker-check
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

sync:
	cd $(BACKEND_DIR) && uv sync --all-groups

lint:
	cd $(BACKEND_DIR) && uv run ruff check .

format:
	cd $(BACKEND_DIR) && uv run ruff check . --fix && uv run ruff format .

test-up: docker-check
	$(COMPOSE_TEST) up -d

test-down:
	$(COMPOSE_TEST) down -v

test: test-up
	@echo "Waiting for test Postgres..."
	@sleep 5
	cd $(BACKEND_DIR) && uv run pytest -v
	$(MAKE) test-down

test-unit:
	cd $(BACKEND_DIR) && uv run pytest tests/unit -v

ci: lint test

install:
	@if [ -z "$(DOMAIN)" ]; then \
		echo "Usage: make install DOMAIN=analytics.example.com [USERNAME=admin]"; \
		exit 1; \
	fi
	./deploy/install.sh --domain "$(DOMAIN)" --username "$(USERNAME)"

db: docker-check
	@case "$(filter-out db,$(MAKECMDGOALS))" in \
		migrate) cd $(BACKEND_DIR) && uv run alembic upgrade head ;; \
		backup) \
			mkdir -p $(BACKUP_DIR); \
			out="$(BACKUP_DIR)/$(POSTGRES_DB)_$$(date +%Y%m%d_%H%M%S).dump"; \
			$(COMPOSE) exec -T postgres pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) -Fc > "$$out"; \
			echo "Backup written: $$out"; \
			ls -lh "$$out" ;; \
		*) echo "Unknown db subcommand. Run: make" ;; \
	esac

%:
	@:
