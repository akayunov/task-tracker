from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from tasktracker.core.time import utcnow
from tasktracker.db.models import Task, User
from tasktracker.domain.enums import TaskStatus
from tasktracker.domain.policies import TaskPolicy
from tasktracker.repositories.comment import CommentRepository
from tasktracker.repositories.task import TaskRepository
from tasktracker.repositories.user import UserRepository
from tasktracker.schemas.common import Page, paginate
from tasktracker.schemas.task import TaskCreate, TaskListParams, TaskRead, TaskUpdate


class TaskService:
    """Создание задач, назначение, статус и удаление."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._users = UserRepository(session)
        self._comments = CommentRepository(session)

    async def create(self, actor: User, data: TaskCreate) -> TaskRead:
        """Создать задачу от имени текущего пользователя.

        :param actor: автор
        :param data: поля задачи
        :raises NotFoundError: исполнитель не найден
        :raises ConflictError: исполнитель отключён
        :return: созданная задача
        """
        if data.assignee_id is not None:
            await self._ensure_assignee(data.assignee_id)
        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority,
            status=TaskStatus.TODO,
            author_id=actor.id,
            assignee_id=data.assignee_id,
            due_date=data.due_date,
            completed_at=None,
            version=1,
        )
        await self._tasks.add(task)
        return await self._present(task.id)

    async def get(self, task_id: UUID) -> TaskRead:
        """Карточка задачи.

        :param task_id: первичный ключ
        :raises NotFoundError: задача не найдена
        :return: задача
        """
        task = await self._tasks.get(task_id)
        if task is None:
            raise NotFoundError('Task not found', code='task_not_found')
        count = await self._comments.count_for_task(task_id)
        return TaskRead.from_loaded(task, count)

    async def list_tasks(self, filters: TaskListParams) -> Page[TaskRead]:
        """Список задач команды. Видят все аутентифицированные пользователи.

        :param filters: фильтры и пагинация
        :return: страница задач
        """
        rows, total = await self._tasks.list_filtered(filters)
        items = [TaskRead.from_loaded(task, count) for task, count in rows]
        return paginate(items, total, filters.page, filters.page_size)

    async def update(self, actor: User, task_id: UUID, data: TaskUpdate) -> TaskRead:
        """Обновить поля. version должен совпадать с текущей.

        :param actor: кто правит
        :param task_id: задача
        :param data: частичное тело и version
        :raises NotFoundError: задача или исполнитель не найдены
        :raises ConflictError: устаревшая version или неактивный исполнитель
        :raises ForbiddenError: недостаточно прав
        :return: задача после изменения
        """
        task = await self._locked(task_id)
        self._check_version(task, data.version)
        self._check_update_rights(actor, task, data)
        changed = await self._apply_assignee(task, data)
        if self._apply_fields(task, data):
            changed = True
        if changed:
            task.version += 1
        return await self._present(task.id)

    async def complete(self, actor: User, task_id: UUID, version: int) -> TaskRead:
        """Отметить задачу выполненной. Повторный вызов не меняет version.

        :param actor: автор, исполнитель или администратор
        :param task_id: задача
        :param version: ожидаемая версия
        :raises NotFoundError: задача не найдена
        :raises ConflictError: устаревшая version
        :raises ForbiddenError: недостаточно прав
        :return: задача
        """
        task = await self._locked(task_id)
        self._check_version(task, version)
        self._check_status_rights(actor, task)
        if task.status != TaskStatus.DONE:
            self._apply_status(task, TaskStatus.DONE)
            task.version += 1
        return await self._present(task.id)

    async def reopen(self, actor: User, task_id: UUID, version: int) -> TaskRead:
        """Вернуть выполненную задачу в todo.

        :param actor: автор, исполнитель или администратор
        :param task_id: задача
        :param version: ожидаемая версия
        :raises NotFoundError: задача не найдена
        :raises ConflictError: задача не выполнена или version устарела
        :raises ForbiddenError: недостаточно прав
        :return: задача
        """
        task = await self._locked(task_id)
        self._check_version(task, version)
        self._check_status_rights(actor, task)
        if task.status != TaskStatus.DONE:
            raise ConflictError(
                'Only completed tasks can be reopened',
                code='task_not_completed',
            )
        self._apply_status(task, TaskStatus.TODO)
        task.version += 1
        return await self._present(task.id)

    async def delete(self, actor: User, task_id: UUID) -> None:
        """Удалить задачу вместе с комментариями.

        :param actor: автор или администратор
        :param task_id: задача
        :raises NotFoundError: задача не найдена
        :raises ForbiddenError: недостаточно прав
        """
        task = await self._locked(task_id)
        if not TaskPolicy.can_delete(actor, task):
            raise ForbiddenError(
                'Only the author or an administrator can delete this task',
                code='task_delete_forbidden',
            )
        await self._tasks.delete(task)

    async def _locked(self, task_id: UUID) -> Task:
        task = await self._tasks.lock(task_id)
        if task is None:
            raise NotFoundError('Task not found', code='task_not_found')
        return task

    async def _present(self, task_id: UUID) -> TaskRead:
        await self._session.flush()
        current = await self._session.get(Task, task_id)
        if current is not None:
            self._session.expire(current)
        task = await self._tasks.get(task_id)
        if task is None:
            raise NotFoundError('Task not found', code='task_not_found')
        count = await self._comments.count_for_task(task_id)
        return TaskRead.from_loaded(task, count)

    async def _ensure_assignee(self, user_id: UUID) -> None:
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError('Assignee not found', code='assignee_not_found')
        if not user.is_active:
            raise ConflictError('Assignee is inactive', code='assignee_inactive')

    async def _apply_assignee(self, task: Task, data: TaskUpdate) -> bool:
        if 'assignee_id' not in data.model_fields_set:
            return False
        if data.assignee_id == task.assignee_id:
            return False
        if data.assignee_id is not None:
            await self._ensure_assignee(data.assignee_id)
        task.assignee_id = data.assignee_id
        return True

    def _apply_fields(self, task: Task, data: TaskUpdate) -> bool:
        changed = False
        fields = data.model_fields_set
        if 'title' in fields and data.title is not None and data.title != task.title:
            task.title = data.title
            changed = True
        if 'description' in fields and data.description != task.description:
            task.description = data.description
            changed = True
        if 'priority' in fields and data.priority is not None and data.priority != task.priority:
            task.priority = data.priority
            changed = True
        if 'due_date' in fields and data.due_date != task.due_date:
            task.due_date = data.due_date
            changed = True
        if 'status' in fields and data.status is not None and data.status != task.status:
            self._apply_status(task, data.status)
            changed = True
        return changed

    def _apply_status(self, task: Task, status: TaskStatus) -> None:
        task.status = status
        if status == TaskStatus.DONE:
            task.completed_at = utcnow()
            return
        task.completed_at = None

    def _check_version(self, task: Task, version: int) -> None:
        if task.version != version:
            raise ConflictError(
                'The task was updated by another request. Refresh and retry.',
                code='task_version_conflict',
            )

    def _check_update_rights(self, actor: User, task: Task, data: TaskUpdate) -> None:
        fields = data.model_fields_set - {'version'}
        content_fields = fields & {'title', 'description', 'priority', 'due_date', 'assignee_id'}
        if content_fields and not TaskPolicy.can_edit(actor, task):
            raise ForbiddenError(
                'Only the author or an administrator can edit this task',
                code='task_edit_forbidden',
            )
        if 'status' in fields:
            self._check_status_rights(actor, task)

    def _check_status_rights(self, actor: User, task: Task) -> None:
        if TaskPolicy.can_change_status(actor, task):
            return
        raise ForbiddenError(
            'Only the author, the assignee, or an administrator can change the task status',
            code='task_status_forbidden',
        )
