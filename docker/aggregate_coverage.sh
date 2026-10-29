#!/bin/sh
set -eu

COVERAGE_HTML_DIR="${COVERAGE_HTML_DIR:-${COVERAGE_DIR}/htmlcov}"
COVERAGE_XML_PATH="${COVERAGE_XML_PATH:-${COVERAGE_HTML_DIR}/coverage.xml}"

mkdir -p "${COVERAGE_DIR}" "${COVERAGE_HTML_DIR}"

if ! ls "${COVERAGE_DIR}"/.coverage* >/dev/null 2>&1; then
  echo "no coverage data files in ${COVERAGE_DIR}" >&2
  exit 1
fi

echo "coverage data files:"
ls -la "${COVERAGE_DIR}"/.coverage* || true

coverage combine
coverage html -d "${COVERAGE_HTML_DIR}"
coverage xml -o "${COVERAGE_XML_PATH}"

FAIL_UNDER="${COVERAGE_FAIL_UNDER:-}"
if [ -n "${FAIL_UNDER}" ]; then
  coverage report --fail-under="${FAIL_UNDER}"
else
  coverage report
fi

# coverage.py пишет htmlcov/.gitignore со "*", мешает закоммитить index.html как превью
rm -f "${COVERAGE_HTML_DIR}/.gitignore"

echo "html report: ${COVERAGE_HTML_DIR}/index.html"
echo "cobertura: ${COVERAGE_XML_PATH}"
