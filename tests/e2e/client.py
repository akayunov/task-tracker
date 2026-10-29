"""HTTP-клиент для декларативных e2e: ходит в живое приложение по URL."""

from __future__ import annotations

import os
from contextvars import ContextVar

import httpx

_client: ContextVar[httpx.Client] = ContextVar('e2e_http_client')

API_PREFIX = os.environ.get('E2E_API_PREFIX', '/api/v1.0')
DEFAULT_BASE_URL = os.environ.get('E2E_BASE_URL', 'http://127.0.0.1:8000')


def get_client() -> httpx.Client:
    """Текущий клиент из фикстуры сессии/теста.

    :return: httpx.Client с base_url окружения
    :raises LookupError: клиент ещё не установлен фикстурой
    """
    return _client.get()


def set_client(client: httpx.Client):
    """Привязать клиент к текущему контексту.

    :param client: открытый httpx.Client
    :return: token для reset
    """
    return _client.set(client)


def reset_client(token) -> None:
    """Сбросить клиент контекста.

    :param token: значение из set_client
    """
    _client.reset(token)


def api_url(path: str) -> str:
    """Собрать путь API с префиксом версии.

    :param path: путь вида /auth/register
    :return: полный путь с префиксом
    """
    if not path.startswith('/'):
        path = f'/{path}'
    return f'{API_PREFIX}{path}'
