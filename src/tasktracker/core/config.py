from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
    )

    app_name: str = 'Task Tracker'
    app_version: str = '0.1.0'
    environment: Literal['local', 'test', 'production'] = 'local'
    debug: bool = False
    api_prefix: str = '/api/v1.0'
    log_level: str = 'INFO'

    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)

    # Строка через запятую, не JSON: пустое значение отключает CORS.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_full_name: str = 'Administrator'

    @field_validator('database_url')
    @classmethod
    def database_url_must_be_asyncpg(cls, value: str) -> str:
        if not value.startswith('postgresql+asyncpg://'):
            raise ValueError('database_url must start with postgresql+asyncpg://')
        return value

    @field_validator('cors_origins', mode='before')
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            if not value.strip():
                return []
            return [item.strip() for item in value.split(',') if item.strip()]
        return value

    @field_validator('bootstrap_admin_email', 'bootstrap_admin_password', mode='before')
    @classmethod
    def empty_string_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator('bootstrap_admin_email')
    @classmethod
    def normalize_admin_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @model_validator(mode='after')
    def production_guards(self) -> 'Settings':
        if self.environment == 'production':
            if self.debug:
                raise ValueError('debug must be disabled in production')
            if 'dev-only' in self.jwt_secret_key:
                raise ValueError('JWT_SECRET_KEY must be set explicitly in production')
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
