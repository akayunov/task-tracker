from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from tasktracker.api.deps import CurrentUser, DbSession
from tasktracker.core.config import get_settings
from tasktracker.schemas.common import Page
from tasktracker.schemas.task import (
    TaskCreate,
    TaskListParams,
    TaskRead,
    TaskUpdate,
    VersionedAction,
)
from tasktracker.services.task import TaskService

router = APIRouter()


@router.post('', status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    response: Response,
    actor: CurrentUser,
    session: DbSession,
) -> TaskRead:
    """Создать задачу. Исполнитель необязателен."""
    task = await TaskService(session).create(actor, payload)
    prefix = get_settings().api_v1_prefix
    # код возврата 201, так что переход по ссылке на усмотрение клиента
    response.headers['Location'] = f'{prefix}/tasks/{task.id}'
    return task


@router.get('')
async def list_tasks(
    session: DbSession,
    _actor: CurrentUser,
    filters: Annotated[TaskListParams, Query()],
) -> Page[TaskRead]:
    """Список задач команды с фильтрами и пагинацией."""
    return await TaskService(session).list_tasks(filters)


@router.get('/{task_id}')
async def get_task(task_id: UUID, session: DbSession, _actor: CurrentUser) -> TaskRead:
    """Карточка задачи."""
    return await TaskService(session).get(task_id)


@router.patch('/{task_id}')
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    actor: CurrentUser,
    session: DbSession,
) -> TaskRead:
    """Изменить задачу. Нужна актуальная version."""
    return await TaskService(session).update(actor, task_id, payload)


@router.post('/{task_id}/complete')
async def complete_task(
    task_id: UUID,
    payload: VersionedAction,
    actor: CurrentUser,
    session: DbSession,
) -> TaskRead:
    """Отметить задачу выполненной."""
    return await TaskService(session).complete(actor, task_id, payload.version)


@router.post('/{task_id}/reopen')
async def reopen_task(
    task_id: UUID,
    payload: VersionedAction,
    actor: CurrentUser,
    session: DbSession,
) -> TaskRead:
    """Вернуть выполненную задачу в статус todo."""
    return await TaskService(session).reopen(actor, task_id, payload.version)


@router.delete('/{task_id}', status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_task(
    task_id: UUID,
    actor: CurrentUser,
    session: DbSession,
) -> Response:
    """Удалить задачу и её комментарии."""
    await TaskService(session).delete(actor, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
