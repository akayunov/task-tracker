from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tasktracker.db.models import Comment, Task
from tasktracker.repositories.query import escape_like
from tasktracker.schemas.task import TaskListParams

_TASK_SORT = {
    'created_at': Task.created_at,
    'updated_at': Task.updated_at,
    'due_date': Task.due_date,
    'priority': Task.priority,
    'title': Task.title,
}


class TaskRepository:
    """Запросы задач. Сортировка только по белому списку колонок."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, task: Task) -> Task:
        """Сохранить задачу.

        :param task: новая строка
        :return: строка после flush
        """
        self._session.add(task)
        await self._session.flush()
        return task

    async def get(self, task_id: UUID) -> Task | None:
        """Загрузить задачу вместе с автором и исполнителем.

        :param task_id: первичный ключ
        :return: задача или None
        """
        statement = (
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.author), selectinload(Task.assignee))
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def lock(self, task_id: UUID) -> Task | None:
        """Заблокировать строку на время транзакции и загрузить связи.

        :param task_id: первичный ключ
        :return: задача или None
        """
        locked = select(Task.id).where(Task.id == task_id).with_for_update()
        result = await self._session.execute(locked)
        if result.scalar_one_or_none() is None:
            return None
        return await self.get(task_id)

    async def delete(self, task: Task) -> None:
        """Удалить задачу. Комментарии снимет ON DELETE CASCADE.

        :param task: уже загруженная строка
        """
        await self._session.delete(task)
        await self._session.flush()

    async def exists(self, task_id: UUID) -> bool:
        """Проверить, что задача есть, не загружая связи.

        :param task_id: первичный ключ
        :return: True, если строка существует
        """
        statement = select(Task.id).where(Task.id == task_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def list_filtered(
        self,
        filters: TaskListParams,
    ) -> tuple[list[tuple[Task, int]], int]:
        """Вернуть страницу задач и число комментариев у каждой.

        :param filters: фильтры, сортировка и пагинация
        :return: пары (задача, число комментариев) и общее число задач
        """
        conditions = _conditions(filters)
        comments_count = (
            select(func.count(Comment.id))
            .where(Comment.task_id == Task.id)
            .correlate(Task)
            .scalar_subquery()
        )
        statement = select(Task, comments_count).options(
            selectinload(Task.author),
            selectinload(Task.assignee),
        )
        statement = _where(statement, conditions)
        statement = statement.order_by(_order_by(filters), Task.id.asc())
        offset = (filters.page - 1) * filters.page_size
        statement = statement.offset(offset).limit(filters.page_size)
        rows = await self._session.execute(statement)
        items = [(row[0], int(row[1])) for row in rows.all()]

        count_statement = _where(select(func.count()).select_from(Task), conditions)
        count_result = await self._session.execute(count_statement)
        total = int(count_result.scalar_one())
        return items, total


def _conditions(filters: TaskListParams) -> list:
    conditions = []
    if filters.status is not None:
        conditions.append(Task.status == filters.status)
    if filters.priority is not None:
        conditions.append(Task.priority == filters.priority)
    if filters.assignee_id is not None:
        conditions.append(Task.assignee_id == filters.assignee_id)
    if filters.author_id is not None:
        conditions.append(Task.author_id == filters.author_id)
    if filters.search:
        pattern = f'%{escape_like(filters.search)}%'
        conditions.append(
            or_(
                Task.title.ilike(pattern, escape='\\'),
                Task.description.ilike(pattern, escape='\\'),
            )
        )
    return conditions


def _where(statement, conditions: list):
    if conditions:
        return statement.where(*conditions)
    return statement


def _order_by(filters: TaskListParams):
    column = _TASK_SORT[filters.sort]
    if filters.order == 'desc':
        return column.desc().nulls_last()
    return column.asc().nulls_last()
