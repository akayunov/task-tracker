"""Декларативный ресурс комментария."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Self
from uuid import uuid4

from tests.e2e.client import api_url, get_client
from tests.e2e.resources.base import assert_response
from tests.e2e.resources.task import Task
from tests.e2e.resources.tracking import track, untrack
from tests.e2e.resources.user import User


class Comment:
    """Комментарий к задаче через HTTP."""

    def __init__(
        self,
        task: Task,
        author: User,
        body: str | None = None,
        id: str | None = None,
    ) -> None:
        self.task = task
        self.author = author
        self.body = body or f'e2e-comment-{uuid4().hex[:12]}'
        self.id = id
        self.task_id: str | None = task.id
        self.version: int | None = None

    def create(
        self,
        *,
        status_code: int = HTTPStatus.CREATED,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /tasks/{task_id}/comments.

        :param status_code: ожидаемый HTTP-код (успех — CREATED)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        if self.task.id is None:
            raise RuntimeError('Comment.create() needs a created task')
        client = get_client()
        response = client.post(
            api_url(f'/tasks/{self.task.id}/comments'),
            json={'body': self.body},
            headers=self.author.auth_headers,
        )
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=(
                {
                    'body': self.body.strip(),
                    'version': 1,
                    'task_id': self.task.id,
                    'author': {
                        'email': self.author.email,
                        'full_name': self.author.full_name,
                    },
                }
                if status_code == HTTPStatus.CREATED
                else None
            ),
        )
        if status_code == HTTPStatus.CREATED and body:
            self.id = body['id']
            self.task_id = body['task_id']
            self.body = body['body']
            self.version = body['version']
            track(self)
        return self

    def update(
        self,
        *,
        as_user: User | None = None,
        version: int | None = None,
        body: str | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """PATCH /tasks/{task_id}/comments/{id}.

        :param as_user: кто меняет
        :param version: optimistic lock
        :param body: новый текст
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        if self.id is None or self.task.id is None:
            raise RuntimeError('Comment.update() needs created comment and task')
        actor = as_user or self.author
        new_body = (body if body is not None else self.body).strip()
        lock_version = version if version is not None else self.version
        payload = {'version': lock_version, 'body': new_body}
        client = get_client()
        response = client.patch(
            api_url(f'/tasks/{self.task.id}/comments/{self.id}'),
            json=payload,
            headers=actor.auth_headers,
        )
        changed = new_body != self.body
        assert self.version is not None or status_code != HTTPStatus.OK
        result = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=(
                {
                    'body': new_body,
                    'version': (self.version or 0) + (1 if changed else 0),
                    'task_id': self.task.id,
                    'author': {
                        'email': self.author.email,
                        'full_name': self.author.full_name,
                    },
                }
                if status_code == HTTPStatus.OK
                else None
            ),
        )
        if status_code == HTTPStatus.OK and result:
            self.body = result['body']
            self.version = result['version']
        return self

    def delete(
        self,
        *,
        as_user: User | None = None,
        status_code: int = HTTPStatus.NO_CONTENT,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """DELETE /tasks/{task_id}/comments/{id}.

        :param as_user: кто удаляет
        :param status_code: ожидаемый HTTP-код (успех — NO_CONTENT)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        if self.id is None or self.task.id is None:
            raise RuntimeError('Comment.delete() needs created comment and task')
        actor = as_user or self.author
        client = get_client()
        response = client.delete(
            api_url(f'/tasks/{self.task.id}/comments/{self.id}'),
            headers=actor.auth_headers,
        )
        assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
        )
        if status_code == HTTPStatus.NO_CONTENT:
            untrack(self)
            self.id = None
        return self

    @staticmethod
    def list_comments(
        task: Task,
        actor: User,
        *,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """GET /tasks/{task_id}/comments.

        :param task: задача
        :param actor: кто читает
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :param params: пагинация
        :return: тело ответа
        """
        task_id = task.id
        if task_id is None:
            raise RuntimeError('Comment.list_comments() needs a task id')
        client = get_client()
        response = client.get(
            api_url(f'/tasks/{task_id}/comments'),
            params=params,
            headers=actor.auth_headers,
        )
        return assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=(
                {
                    'page': params.get('page', 1),
                    'page_size': params.get('page_size', 20),
                }
                if status_code == HTTPStatus.OK
                else None
            ),
        )
