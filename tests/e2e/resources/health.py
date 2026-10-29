"""Декларативный ресурс health/ready/root (вне /api)."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Self

from tests.e2e.client import get_client
from tests.e2e.resources.base import ANY, assert_response


class Health:
    """Проверки живости процесса и корневого редиректа."""

    def check(
        self,
        *,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """GET /health.

        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        response = get_client().get('/health')
        assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_headers=({'x-request-id': ANY} if status_code == HTTPStatus.OK else None),
            success_body={'status': 'ok'} if status_code == HTTPStatus.OK else None,
        )
        return self

    def ready(
        self,
        *,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """GET /ready.

        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        response = get_client().get('/ready')
        assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body={'status': 'ready'} if status_code == HTTPStatus.OK else None,
        )
        return self

    def root(
        self,
        *,
        status_code: int = HTTPStatus.TEMPORARY_REDIRECT,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """GET / без следования редиректу.

        :param status_code: ожидаемый HTTP-код (успех — TEMPORARY_REDIRECT)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        response = get_client().get('/', follow_redirects=False)
        assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_headers=(
                {'location': '/docs'} if status_code == HTTPStatus.TEMPORARY_REDIRECT else None
            ),
        )
        return self
