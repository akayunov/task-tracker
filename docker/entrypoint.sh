#!/bin/sh
set -eu

python /app/docker/wait_for_db.py

if [ "${ENABLE_COVERAGE:-false}" = 'true' ]; then
  case "${1:-}" in
    uvicorn|gunicorn|python)
      # COVERAGE_FILE задаёт compose-overlay; parallel-mode дописывает .<host>.<pid>.*
      mkdir -p "$(dirname "${COVERAGE_FILE}")"
      exec coverage run -m "$@"
      ;;
  esac
fi

exec "$@"
