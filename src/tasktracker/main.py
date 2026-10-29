import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from tasktracker.api.errors import register_exception_handlers
from tasktracker.api.health import router as health_router
from tasktracker.api.middleware import RequestContextMiddleware
from tasktracker.api.router import api_router
from tasktracker.core.config import get_settings
from tasktracker.core.logging import configure_logging
from tasktracker.db.session import dispose_engine, session_scope
from tasktracker.services.auth import AuthService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Создать администратора при старте и закрыть пул при остановке."""
    configure_logging()
    settings = get_settings()
    logger.info(f'Starting {settings.app_name} ({settings.environment})')
    async with session_scope() as session:
        await AuthService(session).bootstrap_admin()
    yield
    logger.info('Stopping application')
    await dispose_engine()


async def redirect_to_docs() -> RedirectResponse:
    """Открыть Swagger с корня."""
    return RedirectResponse('/docs')


def create_app() -> FastAPI:
    """Собрать приложение: middleware, ошибки, роуты."""
    configure_logging()
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            'Task management API. Authenticated users create tasks, '
            'assign them, mark them done, and leave comments.'
        ),
        lifespan=lifespan,
        openapi_tags=[
            {'name': 'health', 'description': 'Liveness and readiness probes'},
            {'name': 'auth', 'description': 'Registration and tokens'},
            {'name': 'users', 'description': 'Directory used to assign tasks'},
            {'name': 'tasks', 'description': 'Task management'},
            {'name': 'comments', 'description': 'Comments on tasks'},
        ],
    )
    application.add_middleware(RequestContextMiddleware)
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=['*'],
            allow_headers=['*'],
        )
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router, prefix=settings.api_prefix)
    application.add_api_route('/', redirect_to_docs, include_in_schema=False)
    return application


app = create_app()
