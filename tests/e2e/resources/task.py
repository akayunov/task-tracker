"""Декларативный ресурс задачи."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Self
from uuid import uuid4

from tests.e2e.client import api_url, get_client
from tests.e2e.resources.base import ANY, assert_response, blank_to_none
from tests.e2e.resources.tracking import track, untrack, untrack_matching
from tests.e2e.resources.user import User


class Task:
    """Задача, созданная от имени пользователя через HTTP."""

    def __init__(
        self,
        author: User,
        title: str | None = None,
        description: str | None = None,
        priority: str = 'medium',
        assignee_id: str | None = None,
        due_date: str | None = None,
        id: str | None = None,
    ) -> None:
        self.author = author
        self.title = title or f'e2e-task-{uuid4().hex[:12]}'
        self.description = description
        self.priority = priority
        self.assignee_id = assignee_id
        self.due_date = due_date
        # Явный id — для запросов к несуществующей/уже удалённой задаче без create().
        self.id = id
        self.version: int | None = None
        self.status: str | None = None
        self._body: dict[str, Any] = {}

    def create(
        self,
        *,
        as_user: User | None = None,
        status_code: int = HTTPStatus.CREATED,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /tasks.

        :param as_user: кто создаёт (по умолчанию author)
        :param status_code: ожидаемый HTTP-код (успех — CREATED)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        actor = as_user or self.author
        client = get_client()
        payload: dict[str, Any] = {
            'title': self.title,
            'priority': self.priority,
        }
        if self.description is not None:
            payload['description'] = self.description
        if self.assignee_id is not None:
            payload['assignee_id'] = self.assignee_id
        if self.due_date is not None:
            payload['due_date'] = self.due_date
        response = client.post(api_url('/tasks'), json=payload, headers=actor.auth_headers)
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=(
                {
                    'title': self.title.strip(),
                    'description': blank_to_none(self.description),
                    'priority': self.priority,
                    'status': 'todo',
                    'version': 1,
                    'completed_at': None,
                    'comments_count': 0,
                    'due_date': self.due_date,
                    'author': {'email': actor.email, 'full_name': actor.full_name},
                    'assignee': {'id': self.assignee_id} if self.assignee_id else None,
                }
                if status_code == HTTPStatus.CREATED
                else None
            ),
        )
        if status_code == HTTPStatus.CREATED and body:
            self._apply_body(body)
            location = api_url(f'/tasks/{self.id}')
            assert response.headers.get('location') == location, response.headers.get('location')
            track(self)
        return self

    def get(
        self,
        *,
        as_user: User | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """GET /tasks/{id}.

        :param as_user: кто читает
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        if self.id is None and status_code == HTTPStatus.OK:
            raise RuntimeError('Task.get() needs an id')
        actor = as_user or self.author
        task_id = self.id
        client = get_client()
        response = client.get(api_url(f'/tasks/{task_id}'), headers=actor.auth_headers)
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._known_success_body() if status_code == HTTPStatus.OK else None,
        )
        if status_code == HTTPStatus.OK and body:
            self._apply_body(body)
        return self

    def update(
        self,
        *,
        as_user: User | None = None,
        version: int | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
        **fields: Any,
    ) -> Self:
        """PATCH /tasks/{id}.

        :param as_user: кто меняет
        :param version: optimistic lock (по умолчанию текущая)
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :param fields: поля патча (title, status, assignee_id, ...)
        :return: self
        """
        if self.id is None:
            raise RuntimeError('Task.update() needs an id')
        actor = as_user or self.author
        lock_version = version if version is not None else self.version
        payload = {'version': lock_version, **fields}
        client = get_client()
        response = client.patch(
            api_url(f'/tasks/{self.id}'),
            json=payload,
            headers=actor.auth_headers,
        )
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=(
                self._update_success_body(fields) if status_code == HTTPStatus.OK else None
            ),
        )
        if status_code == HTTPStatus.OK and body:
            self._apply_body(body)
        return self

    def complete(
        self,
        *,
        as_user: User | None = None,
        version: int | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /tasks/{id}/complete.

        :param as_user: кто завершает
        :param version: optimistic lock
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        return self._versioned_action(
            'complete',
            as_user=as_user,
            version=version,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._complete_success_body() if status_code == HTTPStatus.OK else None,
        )

    def reopen(
        self,
        *,
        as_user: User | None = None,
        version: int | None = None,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """POST /tasks/{id}/reopen.

        :param as_user: кто открывает снова
        :param version: optimistic lock
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        return self._versioned_action(
            'reopen',
            as_user=as_user,
            version=version,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=self._reopen_success_body() if status_code == HTTPStatus.OK else None,
        )

    def delete(
        self,
        *,
        as_user: User | None = None,
        status_code: int = HTTPStatus.NO_CONTENT,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> Self:
        """DELETE /tasks/{id}.

        :param as_user: кто удаляет
        :param status_code: ожидаемый HTTP-код (успех — NO_CONTENT)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :return: self
        """
        if self.id is None:
            raise RuntimeError('Task.delete() needs an id')
        actor = as_user or self.author
        client = get_client()
        response = client.delete(api_url(f'/tasks/{self.id}'), headers=actor.auth_headers)
        assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
        )
        if status_code == HTTPStatus.NO_CONTENT:
            task_id = self.id
            untrack_matching(
                lambda resource: getattr(resource, 'task_id', None) == task_id,
            )
            untrack(self)
            self.id = None
        return self

    @staticmethod
    def list_tasks(
        actor: User,
        *,
        status_code: int = HTTPStatus.OK,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """GET /tasks с фильтрами.

        :param actor: кто запрашивает
        :param status_code: ожидаемый HTTP-код (успех — OK)
        :param expected_headers: ожидания HTTP-заголовков
        :param expected_body: ожидания полей JSON-тела
        :param params: query-параметры списка
        :return: тело ответа
        """
        client = get_client()
        response = client.get(api_url('/tasks'), params=params, headers=actor.auth_headers)
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

    def _versioned_action(
        self,
        action: str,
        *,
        as_user: User | None,
        version: int | None,
        status_code: int,
        expected_headers: dict[str, Any] | None,
        expected_body: dict[str, Any] | None,
        success_body: dict[str, Any] | None = None,
    ) -> Self:
        if self.id is None:
            raise RuntimeError(f'Task.{action}() needs an id')
        actor = as_user or self.author
        payload = {'version': version if version is not None else self.version}
        client = get_client()
        response = client.post(
            api_url(f'/tasks/{self.id}/{action}'),
            json=payload,
            headers=actor.auth_headers,
        )
        body = assert_response(
            response,
            status_code=status_code,
            expected_headers=expected_headers,
            expected_body=expected_body,
            success_body=success_body,
        )
        if status_code == HTTPStatus.OK and body:
            self._apply_body(body)
        return self

    def _known_success_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            'author': {'email': self.author.email, 'full_name': self.author.full_name},
        }
        if self.id is not None:
            body['id'] = self.id
        if self.title is not None:
            body['title'] = self.title
        if self.priority is not None:
            body['priority'] = self.priority
        if self.status is not None:
            body['status'] = self.status
        if self.version is not None:
            body['version'] = self.version
        if self.description is not None or self._body:
            body['description'] = self.description
        if self.assignee_id is not None:
            body['assignee'] = {'id': self.assignee_id}
        elif self._body:
            body['assignee'] = None
        return body

    def _update_success_body(self, fields: dict[str, Any]) -> dict[str, Any]:
        title = self.title
        description = self.description
        priority = self.priority
        status = self.status
        due_date = self.due_date
        assignee_id = self.assignee_id
        changed = False

        if 'title' in fields:
            new_title = fields['title'].strip()
            if new_title != self.title:
                changed = True
            title = new_title
        if 'description' in fields:
            new_description = blank_to_none(fields['description'])
            if new_description != self.description:
                changed = True
            description = new_description
        if 'priority' in fields:
            if fields['priority'] != self.priority:
                changed = True
            priority = fields['priority']
        if 'status' in fields:
            if fields['status'] != self.status:
                changed = True
            status = fields['status']
        if 'due_date' in fields:
            if fields['due_date'] != self.due_date:
                changed = True
            due_date = fields['due_date']
        if 'assignee_id' in fields:
            if fields['assignee_id'] != self.assignee_id:
                changed = True
            assignee_id = fields['assignee_id']

        assert self.version is not None
        body: dict[str, Any] = {
            'title': title,
            'description': description,
            'priority': priority,
            'status': status,
            'due_date': due_date,
            'version': self.version + (1 if changed else 0),
            'author': {'email': self.author.email, 'full_name': self.author.full_name},
            'assignee': {'id': assignee_id} if assignee_id else None,
        }
        if status == 'done' and self.status != 'done':
            body['completed_at'] = ANY
        elif status != 'done':
            body['completed_at'] = None
        return body

    def _complete_success_body(self) -> dict[str, Any]:
        assert self.version is not None
        if self.status == 'done':
            return {'status': 'done', 'version': self.version}
        return {
            'status': 'done',
            'version': self.version + 1,
            'completed_at': ANY,
        }

    def _reopen_success_body(self) -> dict[str, Any]:
        assert self.version is not None
        return {
            'status': 'todo',
            'completed_at': None,
            'version': self.version + 1,
        }

    def _apply_body(self, body: dict[str, Any]) -> None:
        self._body = body
        self.id = body['id']
        self.title = body['title']
        self.description = body.get('description')
        self.priority = body['priority']
        self.status = body['status']
        self.version = body['version']
        self.due_date = body.get('due_date')
        assignee = body.get('assignee')
        self.assignee_id = assignee['id'] if assignee else None
