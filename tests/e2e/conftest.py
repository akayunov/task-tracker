"""Фикстуры e2e: только HTTP к живому API, без миграций и TRUNCATE."""

from __future__ import annotations

import os

import pytest

from tests.e2e.client import DEFAULT_BASE_URL, reset_client, set_client
from tests.e2e.resources.tracking import cleanup_tracked


@pytest.fixture(autouse=True)
def e2e_http_client():
    """Синхронный httpx-клиент на E2E_BASE_URL для декларативных ресурсов."""
    import httpx

    base_url = os.environ.get('E2E_BASE_URL', DEFAULT_BASE_URL)
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        token = set_client(client)
        try:
            yield client
        finally:
            reset_client(token)


@pytest.fixture(autouse=True)
def e2e_cleanup(e2e_http_client):
    """После теста удалить созданные ресурсы через API (пока клиент ещё жив)."""
    del e2e_http_client
    yield
    cleanup_tracked()
