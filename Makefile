.PHONY: up down logs test lint migrate

up:
	docker compose up --build -d --force-recreate migrate api tests

down:
	docker compose down

logs:
	docker compose logs -f api db

test:
	docker compose exec tests pytest

lint:
	docker compose exec tests ruff check src tests alembic
	docker compose exec tests ruff format --check src tests alembic
	docker compose exec tests mypy

migrate:
	docker compose up -d db
	docker compose up -d --build --force-recreate --no-deps migrate
	docker compose wait migrate
