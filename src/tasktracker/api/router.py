from fastapi import APIRouter

from tasktracker.api.v1 import auth, comments, tasks, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix='/auth', tags=['auth'])
api_router.include_router(users.router, prefix='/users', tags=['users'])
api_router.include_router(tasks.router, prefix='/tasks', tags=['tasks'])
api_router.include_router(
    comments.router,
    prefix='/tasks/{task_id}/comments',
    tags=['comments'],
)
