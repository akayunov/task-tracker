"""E2E: комментарии."""

from http import HTTPStatus
from uuid import uuid4

import pytest

from tests.e2e.resources.comment import Comment
from tests.e2e.resources.task import Task
from tests.e2e.resources.user import User

pytestmark = pytest.mark.e2e


def test_comment_crud_and_permissions():
    author = User().create()
    other = User().create()
    task = Task(author).create()

    comment = Comment(task, other, body='  Looks good  ').create()

    comment.update(
        as_user=author,
        body='Changed',
        status_code=HTTPStatus.FORBIDDEN,
        expected_body={'code': 'comment_edit_forbidden'},
    )
    comment.update(body='Changed')
    comment.update(
        version=1,
        body='Again',
        status_code=HTTPStatus.CONFLICT,
        expected_body={'code': 'comment_version_conflict'},
    )

    Comment.list_comments(
        task,
        author,
        expected_body={'total': 1, 'items': [{'body': 'Changed'}]},
    )

    comment.delete(
        as_user=author,
        status_code=HTTPStatus.FORBIDDEN,
        expected_body={'code': 'comment_delete_forbidden'},
    )
    comment.delete()
    Comment.list_comments(task, author, expected_body={'total': 0})


def test_cascade_delete_removes_comments():
    author = User().create()
    task = Task(author).create()
    Comment(task, author, body='Still here').create()
    task_id = task.id

    task.delete()

    Comment.list_comments(
        Task(author, id=task_id),
        author,
        status_code=HTTPStatus.NOT_FOUND,
        expected_body={'code': 'task_not_found'},
    )


def test_comment_requires_existing_task():
    author = User().create()
    Comment(Task(author, id=str(uuid4())), author, body='Nobody home').create(
        status_code=HTTPStatus.NOT_FOUND,
        expected_body={'code': 'task_not_found'},
    )


def test_comment_not_found():
    author = User().create()
    task = Task(author).create()
    Comment(task, author, id=str(uuid4())).update(
        body='Nope',
        version=1,
        status_code=HTTPStatus.NOT_FOUND,
        expected_body={'code': 'comment_not_found'},
    )


def test_comment_noop_keeps_version():
    author = User().create()
    task = Task(author).create()
    comment = Comment(task, author, body='Same').create()
    comment.update(body='Same')
