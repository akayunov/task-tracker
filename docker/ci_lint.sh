#!/bin/sh
# Lint без БД: собираем tests-unit и гоняем ruff + mypy с переопределённым entrypoint.
set -eu

COMPOSE='docker compose -f docker-compose.yml'

$COMPOSE build tests-unit
$COMPOSE run --rm --no-deps --entrypoint ruff tests-unit check src tests alembic
$COMPOSE run --rm --no-deps --entrypoint ruff tests-unit format --check src tests alembic
$COMPOSE run --rm --no-deps --entrypoint mypy tests-unit
