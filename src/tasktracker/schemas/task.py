from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tasktracker.domain.enums import TaskPriority, TaskStatus
from tasktracker.schemas.user import UserBrief

if TYPE_CHECKING:
    from tasktracker.db.models import Task


def _strip_title(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError('Title must not be empty')
    return cleaned


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str = Field(min_length=1, max_length=200, examples=['Prepare release notes'])
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    due_date: date | None = None

    @field_validator('title')
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _strip_title(value)

    @field_validator('description')
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class TaskUpdate(BaseModel):
    """Частичное обновление. null у assignee_id и due_date снимает значение."""

    model_config = ConfigDict(extra='forbid')

    version: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None

    @field_validator('title')
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_title(value)

    @field_validator('description')
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @model_validator(mode='after')
    def reject_null_scalars(self) -> Self:
        if 'title' in self.model_fields_set and self.title is None:
            raise ValueError('title cannot be null')
        if 'priority' in self.model_fields_set and self.priority is None:
            raise ValueError('priority cannot be null')
        if 'status' in self.model_fields_set and self.status is None:
            raise ValueError('status cannot be null')
        return self


class VersionedAction(BaseModel):
    model_config = ConfigDict(extra='forbid')

    version: int = Field(ge=1)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    completed_at: datetime | None
    version: int
    author: UserBrief
    assignee: UserBrief | None
    comments_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_loaded(cls, task: Task, comments_count: int) -> TaskRead:
        """Собрать ответ из задачи с уже загруженными author и assignee.

        :param task: ORM-задача
        :param comments_count: число комментариев
        :return: схема ответа
        """
        assignee = task.assignee
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            completed_at=task.completed_at,
            version=task.version,
            author=UserBrief.model_validate(task.author),
            assignee=UserBrief.model_validate(assignee) if assignee is not None else None,
            comments_count=comments_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class TaskListParams(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None
    author_id: UUID | None = None
    search: str | None = Field(default=None, max_length=200)
    sort: Literal['created_at', 'updated_at', 'due_date', 'priority', 'title'] = 'created_at'
    order: Literal['asc', 'desc'] = 'desc'
    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator('search')
    @classmethod
    def strip_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
