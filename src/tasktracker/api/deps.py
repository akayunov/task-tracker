from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.core.config import get_settings
from tasktracker.core.exceptions import UnauthorizedError
from tasktracker.core.security import decode_access_token
from tasktracker.db.models import User
from tasktracker.db.session import get_db
from tasktracker.repositories.user import UserRepository

_settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f'{_settings.api_v1_prefix}/auth/token',
    auto_error=False,
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    session: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    """Вернуть активного пользователя по access-токену.

    :param session: сессия запроса
    :param token: значение Bearer или None
    :raises UnauthorizedError: токен отсутствует, неверен или пользователь отключён
    :return: текущий пользователь
    """
    if token is None:
        raise UnauthorizedError('Not authenticated', code='not_authenticated')
    user = await UserRepository(session).get(decode_access_token(token))
    if user is None or not user.is_active:
        raise UnauthorizedError('Not authenticated', code='not_authenticated')
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
