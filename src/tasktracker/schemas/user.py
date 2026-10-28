from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from tasktracker.domain.enums import UserRole


class UserCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator('full_name')
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Full name must not be empty')
        return cleaned

    @field_validator('password')
    @classmethod
    def password_strength(cls, value: str) -> str:
        has_letter = any(character.isalpha() for character in value)
        has_digit = any(character.isdigit() for character in value)
        if has_letter and has_digit:
            return value
        raise ValueError('Password must contain at least one letter and one digit')


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserBrief(BaseModel):
    """Пользователь в составе задачи или комментария."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str


class UserListParams(BaseModel):
    model_config = ConfigDict(extra='forbid')

    search: str | None = Field(default=None, max_length=200)
    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator('search')
    @classmethod
    def strip_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
