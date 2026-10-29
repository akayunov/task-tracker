"""Декларативный ресурс пользователя (регистрация, auth и удаление по HTTP)."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Self
from uuid import uuid4

from tests.e2e.client import api_url, get_client
from tests.e2e.resources.base import ANY, assert_response
from tests.e2e.resources.tracking import track, untrack


class User:
    """Описание пользователя для HTTP e2e.

    Идентификаторы по умолчанию случайные: email и имя не пересекаются с продовыми.
    После create() ресурс ставится на очистку; delete() деактивирует аккаунт через API.
    """

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        full_name: str | None = None,
        role: str = 'user',
        is_active: bool = True,
        id: str | None = None,
    ) -> None:
        suffix = uuid4().hex
        self.email = email or f'e2e-{suffix}@example.com'
        self.password = password or f'Pass{suffix[:10]}1'
        self.full_name = full_name or f'E2E User {suffix[:8]}'
        self.role = role
        self.is_active = is_active
        self.id = id
        self.created_at: str | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    @property
    def auth_headers(self) -> dict[str, str]:
        """Заголовок Authorization для запросов от этого пользователя.

        Если пользователь ещё не создан и токена нет — заголовок не ставится
        (запрос уходит неаутентифицированным).
        """
        if self._access_token is None and self.id is None:
            return {}
        return {'Authorization': f'Bearer {self._ensure_access_token()}'}

    def create(
        self,
        *,
        role: str | None = None,
        status_code: int = HTTPStatus.CREATED,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /auth/register и сверить ответ с ожиданиями.

        :param role: если задан — попадёт в тело запроса (API должен отклонить)
        :param status_code: ожидаемый HTTP-код (успех — CREATED)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self с заполненными id и created_at
        """
        client = get_client()
        payload: dict[str, Any] = {
            'email': self.email,
            'password': self.password,
            'full_name': self.full_name,
        }
        if role is not None:
            payload['role'] = role
        response = client.post(api_url('/auth/register'), json=payload)
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=(
                {
                    'email': self.email.lower().strip(),
                    'full_name': self.full_name.strip(),
                    'role': self.role,
                    'is_active': self.is_active,
                }
                if status_code == HTTPStatus.CREATED
                else None
            ),
        )
        assert self.password not in response.text
        if status_code == HTTPStatus.CREATED and body:
            assert 'hashed_password' not in response.text
            self.id = body['id']
            self.created_at = body['created_at']
            self.email = body['email']
            self.full_name = body['full_name']
            self.role = body['role']
            self.is_active = body['is_active']
            track(self)
        return self

    def login(
        self,
        *,
        password: str | None = None,
        email: str | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /auth/login.

        :param password: пароль (по умолчанию self.password)
        :param email: email (по умолчанию self.email)
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        client = get_client()
        response = client.post(
            api_url('/auth/login'),
            json={'email': email or self.email, 'password': password or self.password},
        )
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._token_success_body() if status_code == HTTPStatus.OK else None,
        )
        if status_code == HTTPStatus.OK:
            self._store_tokens(body)
        return self

    def token(
        self,
        *,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /auth/token (OAuth2 password form, username = email).

        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        client = get_client()
        response = client.post(
            api_url('/auth/token'),
            data={'username': self.email, 'password': self.password},
        )
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._token_success_body() if status_code == HTTPStatus.OK else None,
        )
        if status_code == HTTPStatus.OK:
            self._store_tokens(body)
        return self

    def refresh(
        self,
        *,
        token: str | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /auth/refresh.

        :param token: refresh-токен (по умолчанию текущий)
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        refresh_token = token if token is not None else self._refresh_token
        if refresh_token is None:
            raise RuntimeError('User.refresh() needs a refresh token')
        client = get_client()
        response = client.post(api_url('/auth/refresh'), json={'refresh_token': refresh_token})
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._token_success_body() if status_code == HTTPStatus.OK else None,
        )
        if status_code == HTTPStatus.OK:
            self._store_tokens(body)
        return self

    def logout(
        self,
        *,
        token: str | None = None,
        status_code: int = HTTPStatus.NO_CONTENT,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /auth/logout.

        :param token: refresh-токен (по умолчанию текущий)
        :param status_code: ожидаемый HTTP-код (успех — NO_CONTENT)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        refresh_token = token if token is not None else self._refresh_token
        if refresh_token is None:
            self.login()
            refresh_token = self._refresh_token
        assert refresh_token is not None
        client = get_client()
        response = client.post(api_url('/auth/logout'), json={'refresh_token': refresh_token})
        assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
        )
        return self

    def me(
        self,
        *,
        access_token: str | None = None,
        authorized: bool = True,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """GET /auth/me.

        :param access_token: явный Bearer (например после delete, когда self-токен сброшен)
        :param authorized: передавать ли Bearer-токен (игнорируется, если задан access_token)
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        client = get_client()
        if access_token is not None:
            headers = {'Authorization': f'Bearer {access_token}'}
        elif authorized:
            headers = self.auth_headers
        else:
            headers = None
        response = client.get(api_url('/auth/me'), headers=headers)
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._profile_success_body() if status_code == HTTPStatus.OK else None,
        )
        if status_code == HTTPStatus.OK and body and self.id is None:
            self.id = body['id']
        return self

    def get(
        self,
        *,
        as_user: User | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """GET /users/{id}.

        :param as_user: кто запрашивает (по умолчанию self)
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        if self.id is None and status_code == HTTPStatus.OK:
            raise RuntimeError('User.get() needs an id')
        actor = as_user or self
        response = get_client().get(
            api_url(f'/users/{self.id}'),
            headers=actor.auth_headers,
        )
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._profile_success_body() if status_code == HTTPStatus.OK else None,
        )
        if status_code == HTTPStatus.OK and body:
            self.email = body['email']
            self.full_name = body['full_name']
            self.role = body['role']
            self.is_active = body['is_active']
        return self

    def list_users(
        self,
        *,
        search: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GET /users от имени этого пользователя.

        :param search: фильтр поиска
        :param page: номер страницы
        :param page_size: размер страницы
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: тело ответа
        """
        client = get_client()
        params: dict[str, Any] = {}
        if search is not None:
            params['search'] = search
        if page is not None:
            params['page'] = page
        if page_size is not None:
            params['page_size'] = page_size
        response = client.get(api_url('/users'), params=params, headers=self.auth_headers)
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=(
                {
                    'page': page if page is not None else 1,
                    'page_size': page_size if page_size is not None else 20,
                }
                if status_code == HTTPStatus.OK
                else None
            ),
        )
        if status_code == HTTPStatus.OK:
            assert 'hashed_password' not in response.text
            for item in body.get('items', []):
                assert 'hashed_password' not in item
        return body

    def delete(
        self,
        *,
        as_user: User | None = None,
        status_code: int = HTTPStatus.NO_CONTENT,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """DELETE /users/{id}: деактивация (is_active=false).

        :param as_user: кто удаляет (по умолчанию self)
        :param status_code: ожидаемый HTTP-код (успех — NO_CONTENT)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        if self.id is None:
            raise RuntimeError('User.delete() needs a created user with id')
        actor = as_user or self
        client = get_client()
        response = client.delete(api_url(f'/users/{self.id}'), headers=actor.auth_headers)
        assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
        )
        if status_code == HTTPStatus.NO_CONTENT:
            untrack(self)
            self._access_token = None
            self._refresh_token = None
            if actor is self:
                self.id = None
        return self

    def _profile_success_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
        }
        if self.id is not None:
            body['id'] = self.id
        return body

    @staticmethod
    def _token_success_body() -> dict[str, Any]:
        return {
            'token_type': 'bearer',
            'access_token': ANY,
            'refresh_token': ANY,
            'expires_in': ANY,
        }

    def _store_tokens(self, body: dict[str, Any]) -> None:
        access_token = body.get('access_token')
        refresh_token = body.get('refresh_token')
        assert access_token, f'access_token missing in auth response: {body!r}'
        assert refresh_token, f'refresh_token missing in auth response: {body!r}'
        self._access_token = access_token
        self._refresh_token = refresh_token

    def _ensure_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        self.login()
        assert self._access_token is not None
        return self._access_token
