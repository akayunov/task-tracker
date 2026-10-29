"""Общие проверки ответа для декларативных ресурсов."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import httpx

# В expected_*: значение должно быть не None (поле/заголовок присутствует).
ANY = object()


def assert_response(
    response: httpx.Response,
    *,
    status_code: int = HTTPStatus.OK,
    expected_headers: dict[str, Any] | None = None,
    expected_body: dict[str, Any] | None = None,
    success_headers: dict[str, Any] | None = None,
    success_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Проверить код, заголовки и поля тела; вернуть JSON.

    На успешном ответе ``success_*`` (вычисленные из аргументов ресурса) сливаются
    с ``expected_*``: явные ожидания теста перекрывают вычисленные.

    :param response: ответ httpx
    :param status_code: ожидаемый HTTP-код
    :param expected_headers: ожидания HTTP-заголовков из теста
    :param expected_body: ожидания полей JSON-тела из теста
    :param success_headers: заголовки, выводимые из аргументов при успехе
    :param success_body: поля тела, выводимые из аргументов при успехе
    :return: разобранное тело ответа (пустой dict для пустого тела)
    :raises AssertionError: код, заголовок или поле не совпали
    """
    headers_expected = {**(success_headers or {}), **(expected_headers or {})}
    body_expected = {**(success_body or {}), **(expected_body or {})}

    assert (
        response.status_code == status_code
    ), f'expected HTTP {status_code}, got {response.status_code}: {response.text}'
    for name, value in headers_expected.items():
        actual = response.headers.get(name)
        if value is ANY:
            assert actual is not None, f'header {name} is missing'
        else:
            assert actual == value, f'header {name}: expected {value!r}, got {actual!r}'
    if status_code == HTTPStatus.NO_CONTENT or not response.content:
        if body_expected:
            raise AssertionError(
                f'expected body fields {body_expected!r}, but response is empty',
            )
        return {}
    body = response.json()
    if body_expected:
        _assert_mapping(body, body_expected)
    return body


def blank_to_none(value: str | None) -> str | None:
    """Как API: пустая/пробельная строка → null."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _assert_mapping(actual: Any, expected: dict[str, Any], path: str = '') -> None:
    assert isinstance(actual, dict), f'{path or "<root>"}: expected object, got {actual!r}'
    for key, value in expected.items():
        dotted = f'{path}.{key}' if path else key
        assert key in actual, f'missing field {dotted!r} in {actual!r}'
        _assert_value(actual[key], value, dotted)


def _assert_value(actual: Any, expected: Any, path: str) -> None:
    if expected is ANY:
        assert actual is not None, f'{path}: expected any value, got None'
        return
    if isinstance(expected, dict):
        _assert_mapping(actual, expected, path)
        return
    if isinstance(expected, list):
        assert isinstance(actual, list), f'{path}: expected list, got {actual!r}'
        assert len(actual) == len(
            expected
        ), f'{path}: expected length {len(expected)}, got {len(actual)}'
        for index, item_expected in enumerate(expected):
            _assert_value(actual[index], item_expected, f'{path}[{index}]')
        return
    assert actual == expected, f'{path}: expected {expected!r}, got {actual!r}'
