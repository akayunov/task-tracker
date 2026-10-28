from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tasktracker.schemas.user import UserBrief

if TYPE_CHECKING:
    from tasktracker.db.models import Comment


def _strip_body(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError('Comment must not be empty')
    return cleaned


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    body: str = Field(min_length=1, max_length=2000)

    @field_validator('body')
    @classmethod
    def clean_body(cls, value: str) -> str:
        return _strip_body(value)


class CommentUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    version: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=2000)

    @field_validator('body')
    @classmethod
    def clean_body(cls, value: str) -> str:
        return _strip_body(value)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    body: str
    version: int
    author: UserBrief
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_loaded(cls, comment: Comment) -> CommentRead:
        return cls(
            id=comment.id,
            task_id=comment.task_id,
            body=comment.body,
            version=comment.version,
            author=UserBrief.model_validate(comment.author),
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )


class CommentListParams(BaseModel):
    model_config = ConfigDict(extra='forbid')

    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=20, ge=1, le=100)
