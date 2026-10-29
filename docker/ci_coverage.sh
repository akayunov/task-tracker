#!/bin/sh
# Локальный one-shot: unit + e2e + отчёт (как раздельные CI stage подряд).
set -eu

OUT_DIR="${1:-.}"

./docker/ci_unit.sh coverage-data/unit
./docker/ci_e2e.sh coverage-data/e2e
./docker/ci_coverage_report.sh coverage-data "${OUT_DIR}"
