#!/bin/sh
# Склеить .coverage* из артефактов unit/e2e, HTML+XML, fail если ниже порога.
set -eu

DATA_ROOT="${1:-coverage-data}"
OUT_DIR="${2:-.}"
COMPOSE='docker compose -f docker-compose.yml -f docker-compose.coverage.yml'

if ! ls "${DATA_ROOT}"/*/.coverage* >/dev/null 2>&1 && ! ls "${DATA_ROOT}"/.coverage* >/dev/null 2>&1; then
  echo "no coverage data under ${DATA_ROOT}" >&2
  exit 1
fi

$COMPOSE build tests-unit

COV_DIR=/tmp/coverage_dir

cid="$(docker create \
  -e COVERAGE_DIR="${COV_DIR}" \
  -e COVERAGE_FILE="${COV_DIR}/.coverage" \
  -e COVERAGE_HTML_DIR=/tmp/htmlcov \
  -e COVERAGE_XML_PATH=/tmp/coverage.xml \
  -e COVERAGE_FAIL_UNDER="${COVERAGE_FAIL_UNDER:-}" \
  --entrypoint sleep \
  task-tracker-tests-unit \
  3600)"

cleanup() {
  docker rm -f "${cid}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker start "${cid}" >/dev/null
docker exec "${cid}" mkdir -p "${COV_DIR}"

# Заливаем все .coverage* из артефактов (unit/, e2e/, …)
find "${DATA_ROOT}" -type f -name '.coverage*' | while IFS= read -r file; do
  docker cp "${file}" "${cid}:${COV_DIR}/$(basename "${file}")"
done

docker exec \
  -e COVERAGE_DIR="${COV_DIR}" \
  -e COVERAGE_FILE="${COV_DIR}/.coverage" \
  -e COVERAGE_HTML_DIR=/tmp/htmlcov \
  -e COVERAGE_XML_PATH=/tmp/coverage.xml \
  -e COVERAGE_FAIL_UNDER="${COVERAGE_FAIL_UNDER:-}" \
  "${cid}" \
  /app/docker/aggregate_coverage.sh

rm -rf "${OUT_DIR}/htmlcov" "${OUT_DIR}/coverage.xml"
docker cp "${cid}:/tmp/htmlcov" "${OUT_DIR}/htmlcov"
docker cp "${cid}:/tmp/coverage.xml" "${OUT_DIR}/coverage.xml"
