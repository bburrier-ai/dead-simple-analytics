-include .env
export

COMPOSE_TEST_PROJECT ?= dsa-test
TEST_POSTGRES_PORT ?= 5434

COMPOSE := docker compose -f docker-compose.yml
COMPOSE_TEST := docker compose -p $(COMPOSE_TEST_PROJECT) -f docker-compose.test.yml
BACKEND_DIR := backend

POSTGRES_USER ?= dsa
POSTGRES_DB ?= dead_simple_analytics
BACKUP_DIR := backups/db

DOMAIN ?=
USERNAME ?= admin

.DEFAULT_GOAL := help

.PHONY: help docker-check up down status logs sync lint format audit test test-unit test-watchdog ci test-up test-down db install

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
	@echo "  make sync            Install backend deps from hashed uv.lock (--frozen)"
	@echo "  make lint            Run backend ruff lint (includes security rules)"
	@echo "  make format          Run backend ruff format + fix"
	@echo "  make audit           Scan locked deps for known CVEs (pip-audit)"
	@echo ""
	@echo "  make test            Run backend tests (unit+integration, 100% coverage gate)"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-watchdog   Run deployment watchdog tests"
	@echo "  make ci              lint + audit + test + watchdog"
	@echo "  make test-up         Start test Postgres on :$(TEST_POSTGRES_PORT)"
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
	cd $(BACKEND_DIR) && uv sync --frozen --all-groups

lint:
	cd $(BACKEND_DIR) && uv run ruff check .

format:
	cd $(BACKEND_DIR) && uv run ruff check . --fix && uv run ruff format .

audit:
	cd $(BACKEND_DIR) && uv export --frozen --no-dev --no-emit-project -o .requirements-audit.txt
	cd $(BACKEND_DIR) && uvx pip-audit -r .requirements-audit.txt --disable-pip --no-deps

test-up: docker-check
	$(COMPOSE_TEST) up -d --wait

test-down:
	$(COMPOSE_TEST) down -v

test: docker-check
	@set -eu; \
	project="dsa-test-$$(date +%s)-$$$$"; \
	compose() { TEST_POSTGRES_PORT=0 docker compose -p "$$project" -f docker-compose.test.yml "$$@"; }; \
	cleanup() { compose down -v; }; \
	trap cleanup EXIT; \
	compose up -d --wait; \
	published="$$(compose port postgres 5432)"; \
	port="$${published##*:}"; \
	test -n "$$port"; \
	(cd $(BACKEND_DIR) && \
	TEST_DATABASE_URL="postgresql+psycopg://dsa:dsa_dev_password@127.0.0.1:$$port/dead_simple_analytics_test" \
	uv run pytest -v)

test-unit:
	cd $(BACKEND_DIR) && uv run pytest tests/unit -v

test-watchdog:
	bash deploy/test_watchdog.sh

ci: lint audit test test-watchdog

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
