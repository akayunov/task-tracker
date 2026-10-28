from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.db.models import User
from tasktracker.repositories.query import escape_like


class UserRepository:
    """Чтение и запись пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        """Сохранить нового пользователя и получить id.

        :param user: ещё не сохранённая строка
        :return: тот же объект после flush
        """
        self._session.add(user)
        await self._session.flush()
        return user

    async def get(self, user_id: UUID) -> User | None:
        """Найти пользователя по id.

        :param user_id: первичный ключ
        :return: пользователь или None
        """
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Найти пользователя по уже нормализованному email.

        :param email: email в нижнем регистре
        :return: пользователь или None
        """
        statement = select(User).where(User.email == email)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        search: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        """Активные пользователи для назначения задач.

        :param search: фрагмент email или имени
        :param page: номер страницы с 1
        :param page_size: размер страницы
        :return: строки страницы и общее число
        """
        conditions: list = [User.is_active.is_(True)]
        if search:
            pattern = f'%{escape_like(search)}%'
            conditions.append(
                or_(
                    User.email.ilike(pattern, escape='\\'),
                    User.full_name.ilike(pattern, escape='\\'),
                )
            )
        statement = select(User).where(*conditions)
        statement = statement.order_by(User.full_name.asc(), User.id.asc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        rows = await self._session.execute(statement)
        items = list(rows.scalars().all())

        count_statement = select(func.count()).select_from(User).where(*conditions)
        count_result = await self._session.execute(count_statement)
        total = int(count_result.scalar_one())
        return items, total
