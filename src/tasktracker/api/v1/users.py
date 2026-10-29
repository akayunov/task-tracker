from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from tasktracker.api.deps import CurrentUser, DbSession
from tasktracker.schemas.common import Page
from tasktracker.schemas.user import UserListParams, UserRead
from tasktracker.services.user import UserService

router = APIRouter()


@router.get('')
async def list_users(
    session: DbSession,
    _actor: CurrentUser,
    params: Annotated[UserListParams, Query()],
) -> Page[UserRead]:
    """Активные пользователи, которым можно назначить задачу."""
    return await UserService(session).list_users(params)


@router.get('/{user_id}')
async def get_user(user_id: UUID, session: DbSession, _actor: CurrentUser) -> UserRead:
    """Профиль пользователя."""
    return await UserService(session).get(user_id)


@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_user(
    user_id: UUID,
    session: DbSession,
    actor: CurrentUser,
) -> Response:
    """Деактивировать свой аккаунт или любой — для администратора (is_active=false)."""
    await UserService(session).delete(actor, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
