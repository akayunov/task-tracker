#!/bin/sh
# Unit-тесты под coverage; сырые .coverage* → OUT_DIR (артефакт для stage coverage).
set -eu

COMPOSE='docker compose -f docker-compose.yml -f docker-compose.coverage.yml'
OUT_DIR="${1:-coverage-data/unit}"

cleanup() {
  if [ "${DONT_CLEANUP:-}" = '1' ]; then
    return
  fi
  $COMPOSE --profile coverage-report down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

$COMPOSE --profile coverage-report down --remove-orphans >/dev/null 2>&1 || true
$COMPOSE up --build -d --force-recreate db coverage-init migrate tests-unit
$COMPOSE exec -T tests-unit coverage run -m pytest tests/unit -q

COMPOSE="$COMPOSE" ./docker/extract_coverage_data.sh "${OUT_DIR}"
