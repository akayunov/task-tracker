from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.db.session import get_db

router = APIRouter(tags=['health'])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get('/health')
async def health() -> dict[str, str]:
    """Процесс жив и принимает запросы."""
    return {'status': 'ok'}


@router.get('/ready', response_model=None)
async def readiness(session: DbSession) -> JSONResponse:
    """База отвечает. Эту ручку смотрит healthcheck контейнера."""
    try:
        await session.execute(text('SELECT 1'))
    except SQLAlchemyError:
        await session.rollback()
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={'status': 'not_ready', 'code': 'database_unavailable'},
        )
    return JSONResponse(content={'status': 'ready'})
