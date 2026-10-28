from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tasktracker.db.models import Comment


class CommentRepository:
    """Комментарии одной задачи."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, comment: Comment) -> Comment:
        """Сохранить комментарий.

        :param comment: новая строка
        :return: строка после flush
        """
        self._session.add(comment)
        await self._session.flush()
        return comment

    async def count_for_task(self, task_id: UUID) -> int:
        """Посчитать комментарии задачи.

        :param task_id: задача
        :return: число строк
        """
        statement = select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_for_task(self, task_id: UUID, comment_id: UUID) -> Comment | None:
        """Загрузить комментарий только если он принадлежит задаче.

        :param task_id: задача из пути
        :param comment_id: комментарий
        :return: комментарий с автором или None
        """
        statement = (
            select(Comment)
            .where(Comment.id == comment_id, Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def lock(self, task_id: UUID, comment_id: UUID) -> Comment | None:
        """Заблокировать комментарий этой задачи.

        :param task_id: задача из пути
        :param comment_id: комментарий
        :return: комментарий или None, если пара не найдена
        """
        statement = (
            select(Comment.id)
            .where(Comment.id == comment_id, Comment.task_id == task_id)
            .with_for_update()
        )
        result = await self._session.execute(statement)
        if result.scalar_one_or_none() is None:
            return None
        return await self.get_for_task(task_id, comment_id)

    async def list_for_task(
        self,
        task_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[Comment], int]:
        """Страница комментариев в хронологическом порядке.

        :param task_id: задача
        :param page: номер страницы с 1
        :param page_size: размер страницы
        :return: комментарии и общее число
        """
        statement = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = await self._session.execute(statement)
        items = list(rows.scalars().all())
        count_statement = (
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )
        count_result = await self._session.execute(count_statement)
        return items, int(count_result.scalar_one())

    async def delete(self, comment: Comment) -> None:
        """Удалить комментарий.

        :param comment: уже загруженная строка
        """
        await self._session.delete(comment)
        await self._session.flush()
