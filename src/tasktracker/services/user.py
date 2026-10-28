from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.core.exceptions import NotFoundError
from tasktracker.repositories.user import UserRepository
from tasktracker.schemas.common import Page, paginate
from tasktracker.schemas.user import UserListParams, UserRead


class UserService:
    """Справочник пользователей для назначения задач."""

    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)

    async def get(self, user_id: UUID) -> UserRead:
        """Вернуть профиль по id, в том числе неактивный.

        Неактивный профиль остаётся читаемым: он может числиться исполнителем старых задач.

        :param user_id: первичный ключ
        :raises NotFoundError: пользователь не найден
        :return: публичный профиль
        """
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError('User not found', code='user_not_found')
        return UserRead.model_validate(user)

    async def list_users(self, params: UserListParams) -> Page[UserRead]:
        """Список активных коллег.

        :param params: поиск и пагинация
        :return: страница профилей
        """
        items, total = await self._users.list_active(
            params.search,
            params.page,
            params.page_size,
        )
        profiles = [UserRead.model_validate(item) for item in items]
        return paginate(profiles, total, params.page, params.page_size)
