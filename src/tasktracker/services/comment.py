from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from tasktracker.db.models import Comment, User
from tasktracker.domain.policies import CommentPolicy
from tasktracker.repositories.comment import CommentRepository
from tasktracker.repositories.task import TaskRepository
from tasktracker.schemas.comment import CommentCreate, CommentListParams, CommentRead, CommentUpdate
from tasktracker.schemas.common import Page, paginate
from tasktracker.schemas.user import UserBrief


class CommentService:
    """Комментарии к задаче."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._comments = CommentRepository(session)

    async def create(self, actor: User, task_id: UUID, data: CommentCreate) -> CommentRead:
        """Добавить комментарий.

        :param actor: автор комментария
        :param task_id: задача
        :param data: текст
        :raises NotFoundError: задача не найдена
        :return: комментарий
        """
        await self._require_task(task_id)
        comment = Comment(
            task_id=task_id,
            author_id=actor.id,
            body=data.body,
            version=1,
        )
        await self._comments.add(comment)
        return CommentRead(
            id=comment.id,
            task_id=comment.task_id,
            body=comment.body,
            version=comment.version,
            author=UserBrief.model_validate(actor),
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )

    async def list_comments(
        self,
        task_id: UUID,
        params: CommentListParams,
    ) -> Page[CommentRead]:
        """Комментарии задачи от старых к новым.

        :param task_id: задача
        :param params: пагинация
        :raises NotFoundError: задача не найдена
        :return: страница комментариев
        """
        await self._require_task(task_id)
        items, total = await self._comments.list_for_task(
            task_id,
            params.page,
            params.page_size,
        )
        comments = [CommentRead.from_loaded(item) for item in items]
        return paginate(comments, total, params.page, params.page_size)

    async def update(
        self,
        actor: User,
        task_id: UUID,
        comment_id: UUID,
        data: CommentUpdate,
    ) -> CommentRead:
        """Изменить свой комментарий.

        :param actor: автор или администратор
        :param task_id: задача
        :param comment_id: комментарий
        :param data: новый текст и version
        :raises NotFoundError: задача или комментарий не найдены
        :raises ConflictError: устаревшая version
        :raises ForbiddenError: недостаточно прав
        :return: комментарий
        """
        await self._require_task(task_id)
        comment = await self._locked(task_id, comment_id)
        if comment.version != data.version:
            raise ConflictError(
                'The comment was updated by another request. Refresh and retry.',
                code='comment_version_conflict',
            )
        if not CommentPolicy.can_modify(actor, comment):
            raise ForbiddenError(
                'Only the author or an administrator can edit this comment',
                code='comment_edit_forbidden',
            )
        if comment.body != data.body:
            comment.body = data.body
            comment.version += 1
        return await self._present(task_id, comment.id)

    async def delete(self, actor: User, task_id: UUID, comment_id: UUID) -> None:
        """Удалить комментарий.

        :param actor: автор или администратор
        :param task_id: задача
        :param comment_id: комментарий
        :raises NotFoundError: задача или комментарий не найдены
        :raises ForbiddenError: недостаточно прав
        """
        await self._require_task(task_id)
        comment = await self._locked(task_id, comment_id)
        if not CommentPolicy.can_modify(actor, comment):
            raise ForbiddenError(
                'Only the author or an administrator can delete this comment',
                code='comment_delete_forbidden',
            )
        await self._comments.delete(comment)

    async def _require_task(self, task_id: UUID) -> None:
        if not await self._tasks.exists(task_id):
            raise NotFoundError('Task not found', code='task_not_found')

    async def _locked(self, task_id: UUID, comment_id: UUID) -> Comment:
        comment = await self._comments.lock(task_id, comment_id)
        if comment is None:
            raise NotFoundError('Comment not found', code='comment_not_found')
        return comment

    async def _present(self, task_id: UUID, comment_id: UUID) -> CommentRead:
        await self._session.flush()
        current = await self._session.get(Comment, comment_id)
        if current is not None:
            self._session.expire(current)
        comment = await self._comments.get_for_task(task_id, comment_id)
        if comment is None:
            raise NotFoundError('Comment not found', code='comment_not_found')
        return CommentRead.from_loaded(comment)
