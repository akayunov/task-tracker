from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TokenResponse(BaseModel):
    """Пара токенов. Refresh хранится у клиента и отзывается на сервере."""

    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int


class LoginRequest(BaseModel):
    """JSON-вход. Поле email передаётся как username в OAuth2-форме."""

    model_config = ConfigDict(extra='forbid')

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    refresh_token: str = Field(min_length=1, max_length=512)


class LogoutRequest(RefreshRequest):
    """Тело выхода. Отзыв идемпотентен."""
