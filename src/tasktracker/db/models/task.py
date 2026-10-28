from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tasktracker.db.base import Base, TimestampMixin
from tasktracker.db.types import pg_enum
from tasktracker.domain.enums import TaskPriority, TaskStatus

if TYPE_CHECKING:
    from tasktracker.db.models.comment import Comment
    from tasktracker.db.models.user import User


class Task(TimestampMixin, Base):
    """Задача. Комментарии удаляет база через ON DELETE CASCADE."""

    __tablename__ = 'tasks'
    __table_args__ = (
        CheckConstraint('char_length(title) BETWEEN 1 AND 200', name='ck_tasks_title_length'),
        CheckConstraint(
            'description IS NULL OR char_length(description) <= 5000',
            name='ck_tasks_description_length',
        ),
        CheckConstraint('version >= 1', name='ck_tasks_version_positive'),
        CheckConstraint(
            "(status = 'done' AND completed_at IS NOT NULL) "
            "OR (status <> 'done' AND completed_at IS NULL)",
            name='ck_tasks_completed_at_matches_status',
        ),
        Index('ix_tasks_author_id', 'author_id'),
        Index('ix_tasks_assignee_id', 'assignee_id'),
        Index('ix_tasks_created_at', 'created_at'),
        Index('ix_tasks_status_created_at', 'status', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        pg_enum(TaskStatus, 'task_status'),
        default=TaskStatus.TODO,
        server_default=text("'todo'::task_status"),
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        pg_enum(TaskPriority, 'task_priority'),
        default=TaskPriority.MEDIUM,
        server_default=text("'medium'::task_priority"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('users.id', name='fk_tasks_author_id_users', ondelete='RESTRICT'),
        nullable=False,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('users.id', name='fk_tasks_assignee_id_users', ondelete='SET NULL'),
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text('1'),
        nullable=False,
    )

    author: Mapped[User] = relationship(
        foreign_keys=[author_id],
        lazy='raise',
        overlaps='assignee',
    )
    assignee: Mapped[User | None] = relationship(
        foreign_keys=[assignee_id],
        lazy='raise',
        overlaps='author',
    )
    # Не читаем коллекцию при DELETE: строки снимет ON DELETE CASCADE.
    comments: Mapped[list[Comment]] = relationship(
        back_populates='task',
        cascade='save-update, merge',
        passive_deletes=True,
        lazy='raise',
    )
