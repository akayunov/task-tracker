import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tasktracker.core.exceptions import AppError
from tasktracker.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

_SECRET_FIELDS = {'password', 'refresh_token', 'access_token', 'hashed_password'}
_HTTP_CODES = {
    status.HTTP_401_UNAUTHORIZED: 'not_authenticated',
    status.HTTP_403_FORBIDDEN: 'forbidden',
    status.HTTP_404_NOT_FOUND: 'not_found',
    status.HTTP_405_METHOD_NOT_ALLOWED: 'method_not_allowed',
}


def register_exception_handlers(app: FastAPI) -> None:
    """Подключить единый формат ошибок."""
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # подсказка для тайп линтера
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(request, detail=exc.message, code=exc.code),
        headers=_auth_header(exc.status_code),
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # подсказка для тайп линтера
        raise exc
    detail = exc.detail if isinstance(exc.detail, str) else 'Request failed'
    code = _HTTP_CODES.get(exc.status_code, 'http_error')
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(request, detail=detail, code=code),
        headers=_auth_header(exc.status_code),
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # подсказка для тайп линтера
        raise exc
    errors = _hide_secrets(jsonable_encoder(exc.errors()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_body(
            request,
            detail='Request validation failed',
            code='validation_error',
            errors=errors,
        ),
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f'Unhandled error on {request.method} {request.url.path}')
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_body(request, detail='Internal server error', code='internal_error'),
    )


def _body(request: Request, **payload: Any) -> dict[str, Any]:
    del request
    request_id = request_id_ctx.get()
    if request_id != '-':
        payload['request_id'] = request_id
    return payload


def _auth_header(status_code: int) -> dict[str, str] | None:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return {'WWW-Authenticate': 'Bearer'}
    return None


def _hide_secrets(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for error in errors:
        item = dict(error)
        location = item.get('loc', ())
        if any(part in _SECRET_FIELDS for part in location):
            item.pop('input', None)
        cleaned.append(item)
    return cleaned
