import logging
import time
import uuid

from fastapi import status
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from tasktracker.core.logging import request_id_ctx

logger = logging.getLogger('tasktracker.access')


class RequestContextMiddleware:
    """Проставляет X-Request-ID и пишет одну строку на запрос."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        request_id = _header(scope, b'x-request-id') or str(uuid.uuid4())
        # Starlette оборачивает dict в Request.state. Готовый State туда класть нельзя.
        state = scope.get('state')
        if not isinstance(state, dict):
            state = {}
            scope['state'] = state
        state['request_id'] = request_id
        token = request_id_ctx.set(request_id)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        started = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message['type'] == 'http.response.start':
                status_code = message['status']
                headers = MutableHeaders(scope=message)
                headers.append('X-Request-ID', request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                f'{scope["method"]} {scope["path"]} -> {status_code} ({duration_ms:.2f}ms)',
            )
            request_id_ctx.reset(token)


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope['headers']:
        if key == name:
            return value.decode()
    return None
