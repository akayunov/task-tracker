#!/bin/sh
# Скопировать сырые .coverage* из volume наружу (для артефактов между job'ами).
set -eu

COMPOSE="${COMPOSE:-docker compose -f docker-compose.yml -f docker-compose.coverage.yml}"
OUT_DIR="${1:-coverage-data}"

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

cid="$($COMPOSE run -d --no-deps --entrypoint sleep tests-unit 120)"
cleanup_cid() {
  docker rm -f "${cid}" >/dev/null 2>&1 || true
}
trap cleanup_cid EXIT

# Список файлов внутри контейнера → docker cp по одному
files="$(docker exec "${cid}" sh -c 'ls -1 /app/coverage_dir/.coverage* 2>/dev/null' || true)"
if [ -z "${files}" ]; then
  echo "no coverage data files in volume" >&2
  exit 1
fi

echo "${files}" | while IFS= read -r path; do
  [ -n "${path}" ] || continue
  docker cp "${cid}:${path}" "${OUT_DIR}/"
done

echo "extracted coverage data to ${OUT_DIR}:"
ls -la "${OUT_DIR}"
