from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tasktracker.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from tasktracker.db.models.task import Task
    from tasktracker.db.models.user import User


class Comment(TimestampMixin, Base):
    __tablename__ = 'comments'
    __table_args__ = (
        CheckConstraint('char_length(body) BETWEEN 1 AND 2000', name='ck_comments_body_length'),
        CheckConstraint('version >= 1', name='ck_comments_version_positive'),
        Index('ix_comments_author_id', 'author_id'),
        Index('ix_comments_task_id_created_at', 'task_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('tasks.id', name='fk_comments_task_id_tasks', ondelete='CASCADE'),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('users.id', name='fk_comments_author_id_users', ondelete='RESTRICT'),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text('1'), nullable=False
    )

    task: Mapped[Task] = relationship(back_populates='comments', lazy='raise')
    author: Mapped[User] = relationship(lazy='raise')
