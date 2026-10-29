FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_EXTRA_INDEX_URL=https://mirror.yandex.ru/pypi/web/simple \
    POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app


FROM base AS poetry

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
COPY pyproject.toml poetry.lock ./


FROM poetry AS builder

RUN poetry install --no-root --only main


FROM builder AS test-builder

RUN poetry install --no-root --with dev


FROM base AS runtime

ENV PYTHONPATH="/app/src"

COPY --from=builder /app/.venv /app/.venv
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY docker ./docker
COPY pyproject.toml ./pyproject.toml

USER appuser
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "tasktracker.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]


FROM base AS test

ENV PYTEST_CACHE_DIR=/tmp/pytest-cache \
    HOME=/tmp \
    PYTHONPATH="/app/src"

COPY --from=test-builder /app/.venv /app/.venv
COPY src ./src
COPY tests ./tests
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY docker ./docker
COPY pyproject.toml ./pyproject.toml

USER appuser
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["sleep", "infinity"]


FROM poetry AS e2e-builder

RUN poetry install --no-root --only e2e


FROM base AS e2e

ENV PYTEST_CACHE_DIR=/tmp/pytest-cache \
    HOME=/tmp \
    PYTHONPATH="/app"

COPY --from=e2e-builder /app/.venv /app/.venv
COPY tests/__init__.py ./tests/__init__.py
COPY tests/e2e ./tests/e2e
COPY tests/e2e/pyproject.toml ./pyproject.toml

USER appuser
CMD ["sleep", "infinity"]
