.PHONY: up down logs test-unit test-e2e lint migrate coverage

COMPOSE_COV = docker compose -f docker-compose.yml -f docker-compose.coverage.yml

up:
	docker compose up --build -d --force-recreate migrate api tests-unit tests-e2e

down:
	$(COMPOSE_COV) --profile coverage-report down -v --remove-orphans

logs:
	docker compose logs -f api db

test-unit:
	docker compose exec tests-unit pytest tests/unit

# Локально: http://api:8000 в сети edge. С любого хоста против прода:
#   docker run --rm -e E2E_BASE_URL=https://api.example.com task-tracker-tests-e2e \
#     pytest tests/e2e -q
test-e2e:
	docker compose up -d --build tests-e2e
	docker compose exec tests-e2e pytest tests/e2e -q

lint:
	docker compose exec tests-unit ruff check src tests alembic
	docker compose exec tests-unit ruff format --check src tests alembic
	docker compose exec tests-unit mypy

migrate:
	docker compose up -d db
	docker compose up -d --build --force-recreate --no-deps migrate
	docker compose wait migrate

# Long-lived app services that dump coverage on SIGTERM. Add new ones here later.
coverage: COVERAGE_APPS = api
coverage:
	$(COMPOSE_COV) up --build -d --force-recreate coverage-init migrate $(COVERAGE_APPS) tests-unit tests-e2e
	$(COMPOSE_COV) exec tests-unit coverage run -m pytest tests/unit -q
	# e2e бьёт в api под coverage — покрытие приложения дописывается в процесс api
	$(COMPOSE_COV) exec tests-e2e pytest tests/e2e -q
	# SIGTERM so coverage in long-lived app processes flushes parallel data files
	$(COMPOSE_COV) stop $(COVERAGE_APPS)
	$(COMPOSE_COV) --profile coverage-report run --rm --no-deps coverage-report
	./docker/extract_coverage.sh .
	$(COMPOSE_COV) start $(COVERAGE_APPS)
