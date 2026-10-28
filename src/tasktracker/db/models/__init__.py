from sqlalchemy.orm import configure_mappers

from tasktracker.db.models.comment import Comment
from tasktracker.db.models.refresh_token import RefreshToken
from tasktracker.db.models.task import Task
from tasktracker.db.models.user import User

# Проверяем связи сразу, а не на первом запросе.
configure_mappers()

__all__ = ['Comment', 'RefreshToken', 'Task', 'User']
