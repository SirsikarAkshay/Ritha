# Arokah — Developer Makefile
# Usage: make <target>

.PHONY: help install run test migrate seed shell lint fmt docker-up docker-down docker-logs export-data

PYTHON     := python
MANAGE     := $(PYTHON) manage.py
PIP        := pip install --break-system-packages

help:
	@echo ""
	@echo "Arokah Backend — Available Commands"
	@echo "────────────────────────────────────────"
	@echo "  make install        Install all Python dependencies"
	@echo "  make run            Start development server on :8000"
	@echo "  make test           Run full test suite"
	@echo "  make test-fast      Run tests, stop on first failure"
	@echo "  make migrate        Apply database migrations"
	@echo "  make seed           Seed cultural rules + events"
	@echo "  make superuser      Create a Django superuser"
	@echo "  make shell          Open Django shell"
	@echo "  make schema         Generate OpenAPI schema → openapi.yaml"
	@echo "  make daily-looks    Batch-generate today's outfit recommendations"
	@echo "  make export-data    Export user data (GDPR) — EMAIL=user@example.com"
	@echo "  make lint           Run flake8 linter"
	@echo "  make docker-up      Start full stack via docker-compose"
	@echo "  make docker-down    Stop docker-compose stack"
	@echo "  make docker-logs    Follow docker-compose logs"
	@echo ""

install:
	$(PIP) -r requirements.txt

run:
	$(MANAGE) runserver 0.0.0.0:8000

test:
	python -m pytest tests/ -v

test-fast:
	python -m pytest tests/ -x -q

test-coverage:
	python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

migrate:
	$(MANAGE) makemigrations
	$(MANAGE) migrate

migrate:
	$(MANAGE) migrate

migrate-check:
	$(MANAGE) migrate --check

shell:
	$(MANAGE) shell_plus 2>/dev/null || $(MANAGE) shell

schema:
	$(MANAGE) spectacular --file openapi.yaml
	@echo "OpenAPI schema written to openapi.yaml"

seed:
	$(MANAGE) seed_cultural_data

superuser:
	$(MANAGE) createsuperuser

shell:
	$(MANAGE) shell

schema:
	$(MANAGE) spectacular --file openapi.yaml
	@echo "Schema written to openapi.yaml"

daily-looks:
	$(MANAGE) generate_daily_looks --verbosity=2

sync-calendars:
	$(MANAGE) sync_calendars --verbosity=2

sync-all:
	$(MANAGE) sync_calendars --verbosity=1
	$(MANAGE) generate_daily_looks --verbosity=1

register-webhooks:
	$(MANAGE) register_google_webhook --verbosity=2

export-data:
	@if [ -z "$(EMAIL)" ]; then echo "Usage: make export-data EMAIL=user@example.com"; exit 1; fi
	$(MANAGE) export_user_data --email=$(EMAIL) --output=export_$(EMAIL).json

lint:
	flake8 . --max-line-length=120 --exclude=migrations,__pycache__,.venv

fmt:
	black . --line-length=120 --exclude=migrations

docker-up:
	docker-compose up -d
	@echo "API → http://localhost:8000"
	@echo "Docs → http://localhost:8000/api/docs/"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

docker-build:
	docker-compose build --no-cache
