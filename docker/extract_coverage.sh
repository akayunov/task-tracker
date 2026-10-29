#!/bin/sh
# Забрать htmlcov/ и coverage.xml из shared volume coverage_data через docker cp.
set -eu

COMPOSE="${COMPOSE:-docker compose -f docker-compose.yml -f docker-compose.coverage.yml}"
OUT_DIR="${1:-.}"

rm -rf "${OUT_DIR}/htmlcov" "${OUT_DIR}/coverage.xml"
mkdir -p "${OUT_DIR}"

cid="$($COMPOSE run -d --no-deps --entrypoint sleep tests-unit 120)"
cleanup_cid() {
  docker rm -f "${cid}" >/dev/null 2>&1 || true
}
trap cleanup_cid EXIT

docker cp "${cid}:/app/coverage_dir/htmlcov" "${OUT_DIR}/htmlcov"
docker cp "${cid}:/app/coverage_dir/coverage.xml" "${OUT_DIR}/coverage.xml"
