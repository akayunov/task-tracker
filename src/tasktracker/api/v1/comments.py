from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from tasktracker.api.deps import CurrentUser, DbSession
from tasktracker.schemas.comment import CommentCreate, CommentListParams, CommentRead, CommentUpdate
from tasktracker.schemas.common import Page
from tasktracker.services.comment import CommentService

router = APIRouter()


@router.post('', status_code=status.HTTP_201_CREATED)
async def create_comment(
    task_id: UUID,
    payload: CommentCreate,
    actor: CurrentUser,
    session: DbSession,
) -> CommentRead:
    """Добавить комментарий к задаче."""
    return await CommentService(session).create(actor, task_id, payload)


@router.get('')
async def list_comments(
    task_id: UUID,
    session: DbSession,
    _actor: CurrentUser,
    params: Annotated[CommentListParams, Query()],
) -> Page[CommentRead]:
    """Комментарии задачи от старых к новым."""
    return await CommentService(session).list_comments(task_id, params)


@router.patch('/{comment_id}')
async def update_comment(
    task_id: UUID,
    comment_id: UUID,
    payload: CommentUpdate,
    actor: CurrentUser,
    session: DbSession,
) -> CommentRead:
    """Изменить свой комментарий."""
    return await CommentService(session).update(actor, task_id, comment_id, payload)


@router.delete(
    '/{comment_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_comment(
    task_id: UUID,
    comment_id: UUID,
    actor: CurrentUser,
    session: DbSession,
) -> Response:
    """Удалить свой комментарий."""
    await CommentService(session).delete(actor, task_id, comment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
