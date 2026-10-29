from typing import Protocol
from uuid import UUID

from tasktracker.domain.enums import UserRole


class Actor(Protocol):
    id: UUID
    role: UserRole


class TaskAccess(Protocol):
    author_id: UUID
    assignee_id: UUID | None


class CommentAccess(Protocol):
    author_id: UUID


class TaskPolicy:
    @staticmethod
    def can_edit(actor: Actor, task: TaskAccess) -> bool:
        return actor.role == UserRole.ADMIN or task.author_id == actor.id

    @staticmethod
    def can_change_status(actor: Actor, task: TaskAccess) -> bool:
        return (
            actor.role == UserRole.ADMIN
            or task.author_id == actor.id
            or task.assignee_id == actor.id
        )

    @staticmethod
    def can_delete(actor: Actor, task: TaskAccess) -> bool:
        return actor.role == UserRole.ADMIN or task.author_id == actor.id


class CommentPolicy:
    @staticmethod
    def can_modify(actor: Actor, comment: CommentAccess) -> bool:
        return actor.role == UserRole.ADMIN or comment.author_id == actor.id


class UserPolicy:
    @staticmethod
    def can_delete(actor: Actor, target_id: UUID) -> bool:
        return actor.role == UserRole.ADMIN or actor.id == target_id
