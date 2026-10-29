from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.core.exceptions import ForbiddenError, NotFoundError
from tasktracker.db.models import User
from tasktracker.domain.policies import UserPolicy
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

    async def delete(self, actor: User, user_id: UUID) -> None:
        """Деактивировать пользователя (себя или любого — для админа).

        Строка в БД остаётся, ``is_active`` становится false: логин и access
        перестают работать, профиль по id по-прежнему читается.

        :param actor: кто выключает
        :param user_id: кого выключить
        :raises NotFoundError: пользователь не найден
        :raises ForbiddenError: нет права
        """
        if not UserPolicy.can_delete(actor, user_id):
            raise ForbiddenError(
                'Only the account owner or an administrator can delete this user',
                code='user_delete_forbidden',
            )
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError('User not found', code='user_not_found')
        await self._users.deactivate(user)
