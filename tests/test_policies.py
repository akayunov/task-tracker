from uuid import uuid4

from tasktracker.domain.enums import UserRole
from tasktracker.domain.policies import CommentPolicy, TaskPolicy


class _Actor:
    def __init__(self, role: UserRole) -> None:
        self.id = uuid4()
        self.role = role


class _Task:
    def __init__(self, author_id, assignee_id=None) -> None:
        self.author_id = author_id
        self.assignee_id = assignee_id


class _Comment:
    def __init__(self, author_id) -> None:
        self.author_id = author_id


def test_task_policy_matrix():
    author = _Actor(UserRole.USER)
    assignee = _Actor(UserRole.USER)
    stranger = _Actor(UserRole.USER)
    task = _Task(author.id, assignee.id)

    assert TaskPolicy.can_edit(author, task)
    assert not TaskPolicy.can_edit(assignee, task)
    assert TaskPolicy.can_change_status(assignee, task)
    assert not TaskPolicy.can_change_status(stranger, task)
    assert not TaskPolicy.can_delete(assignee, task)


def test_admin_policy_bypass():
    admin = _Actor(UserRole.ADMIN)
    author = _Actor(UserRole.USER)
    task = _Task(author.id)
    comment = _Comment(author.id)

    assert TaskPolicy.can_delete(admin, task)
    assert CommentPolicy.can_modify(admin, comment)
    assert not CommentPolicy.can_modify(_Actor(UserRole.USER), comment)
