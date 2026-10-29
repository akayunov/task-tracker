"""E2E: задачи."""

from http import HTTPStatus
from uuid import uuid4

import pytest

from tests.e2e.resources.base import ANY
from tests.e2e.resources.task import Task
from tests.e2e.resources.user import User

pytestmark = pytest.mark.e2e


def test_create_sets_author():
    author = User(full_name='Author').create()
    task = Task(author, title='  Ship API  ', description='  ').create()
    task.get()


def test_filter_page_and_search():
    author = User().create()
    marker = uuid4().hex[:10]
    Task(author, title=f'{marker} 100% done').create()
    Task(author, title=f'{marker} Other', priority='high').create()
    first = Task(author, title=f'{marker} Alpha').create()
    first.complete()

    # '%' как литерал: среди задач автора с marker в title совпадёт только «100% done»
    Task.list_tasks(
        author,
        search='%',
        author_id=author.id,
        expected_body={'total': 1, 'items': [{'title': f'{marker} 100% done'}]},
    )
    Task.list_tasks(
        author,
        search=f'{marker} 100%',
        author_id=author.id,
        expected_body={'total': 1},
    )
    Task.list_tasks(
        author,
        status='done',
        author_id=author.id,
        page_size=1,
        expected_body={
            'total': 1,
            'pages': 1,
            'items': [{'completed_at': ANY}],
        },
    )
    Task.list_tasks(
        author,
        author_id=author.id,
        page=5,
        expected_body={'total': 3, 'items': []},
    )


def test_assignee_completes_only():
    author = User().create()
    assignee = User(full_name='Assignee').create()
    directory = author.list_users(search=assignee.email)
    assignee_id = directory['items'][0]['id']
    task = Task(author, assignee_id=assignee_id).create()

    task.update(
        as_user=assignee,
        title='Hijacked',
        status_code=HTTPStatus.FORBIDDEN,
        expected_body={'code': 'task_edit_forbidden'},
    )
    task.complete(as_user=assignee)


def test_stranger_cannot_mutate():
    author = User().create()
    stranger = User().create()
    task = Task(author).create()

    task.update(
        as_user=stranger,
        status='in_progress',
        status_code=HTTPStatus.FORBIDDEN,
        expected_body={'code': 'task_status_forbidden'},
    )
    task.delete(
        as_user=stranger,
        status_code=HTTPStatus.FORBIDDEN,
        expected_body={'code': 'task_delete_forbidden'},
    )


def test_version_conflict_and_noop_update():
    author = User().create()
    task = Task(author, title='Same').create()
    original_version = task.version

    task.update(title='Same')
    assert task.version == original_version
    task.update(
        version=99,
        title='Next',
        status_code=HTTPStatus.CONFLICT,
        expected_body={'code': 'task_version_conflict'},
    )


def test_reopen_and_unassign():
    author = User().create()
    assignee = User().create()
    users = author.list_users(search=assignee.email)
    task = Task(
        author,
        assignee_id=users['items'][0]['id'],
        priority='high',
    ).create()

    task.complete()
    task.complete()

    task.reopen(as_user=assignee)
    task.update(assignee_id=None, due_date=None)


def test_unknown_assignee_and_missing_task():
    author = User().create()
    Task(author, title='Orphan', assignee_id=str(uuid4())).create(
        status_code=HTTPStatus.NOT_FOUND,
        expected_body={'code': 'assignee_not_found'},
    )

    Task(author, id=str(uuid4())).get(
        status_code=HTTPStatus.NOT_FOUND,
        expected_body={'code': 'task_not_found'},
    )


def test_unauthenticated_create_is_rejected():
    Task(User(), title='Nope').create(
        status_code=HTTPStatus.UNAUTHORIZED,
        expected_body={'code': 'not_authenticated'},
    )


def test_reopen_not_completed():
    author = User().create()
    task = Task(author).create()
    task.reopen(
        status_code=HTTPStatus.CONFLICT,
        expected_body={'code': 'task_not_completed'},
    )


def test_inactive_assignee_rejected():
    author = User().create()
    assignee = User().create()
    assignee_id = assignee.id
    assignee.delete()
    Task(author, assignee_id=assignee_id).create(
        status_code=HTTPStatus.CONFLICT,
        expected_body={'code': 'assignee_inactive'},
    )
