from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.db.models import RefreshToken


class RefreshTokenRepository:
    """Хранение хешей refresh-токенов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> RefreshToken:
        """Сохранить хеш токена.

        :param token: новая запись
        :return: запись после flush
        """
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Найти токен по sha256-хешу.

        :param token_hash: hex-хеш
        :return: запись или None
        """
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def delete_expired(self, moment: datetime) -> None:
        """Удалить просроченные токены, чтобы таблица не росла бесконечно.

        :param moment: текущее время UTC
        """
        statement = delete(RefreshToken).where(RefreshToken.expires_at < moment)
        await self._session.execute(statement)
