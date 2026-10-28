import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

os.environ['ENVIRONMENT'] = 'test'
os.environ['BOOTSTRAP_ADMIN_EMAIL'] = ''
os.environ['BOOTSTRAP_ADMIN_PASSWORD'] = ''
os.environ['LOG_LEVEL'] = 'WARNING'
os.environ.setdefault(
    'JWT_SECRET_KEY',
    'test-secret-key-must-be-at-least-32-characters',
)
os.environ.setdefault(
    'DATABASE_URL',
    'postgresql+asyncpg://tasktracker:tasktracker@localhost:5432/tasktracker',
)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Накатить миграции на базу из DATABASE_URL."""
    del session
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = f'{result.stdout}\n{result.stderr}'
        raise RuntimeError(details)


@pytest.fixture(autouse=True)
async def clean_database():
    """Очистить таблицы и закрыть пул: следующий тест получит свой event loop."""
    yield
    from sqlalchemy import text

    from tasktracker.db.session import dispose_engine, get_engine

    engine = get_engine()
    statement = 'TRUNCATE TABLE comments, tasks, refresh_tokens, users RESTART IDENTITY CASCADE'
    async with engine.begin() as connection:
        await connection.execute(text(statement))
    await dispose_engine()


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from tasktracker.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as async_client:
        yield async_client
