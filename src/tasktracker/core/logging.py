import logging
from contextvars import ContextVar

from tasktracker.core.config import get_settings

request_id_ctx: ContextVar[str] = ContextVar('request_id', default='-')
_configured = False


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging() -> None:
    """Настроить корневой логгер один раз. Повторный вызов меняет только уровень."""
    global _configured
    settings = get_settings()
    if _configured:
        logging.getLogger().setLevel(settings.log_level.upper())
        return
    logging.basicConfig(
        level=settings.log_level.upper(),
        format='%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s',
        force=True,
    )
    log_filter = RequestIdFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(log_filter)
    logging.getLogger('uvicorn.access').disabled = True
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    _configured = True
