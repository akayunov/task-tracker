import logging
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tasktracker.core.config import get_settings
from tasktracker.core.exceptions import ConflictError, UnauthorizedError
from tasktracker.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
    verify_password_dummy,
)
from tasktracker.core.time import utcnow
from tasktracker.db.errors import constraint_name
from tasktracker.db.models import RefreshToken, User
from tasktracker.domain.enums import UserRole
from tasktracker.repositories.refresh_token import RefreshTokenRepository
from tasktracker.repositories.user import UserRepository
from tasktracker.schemas.auth import TokenResponse
from tasktracker.schemas.user import UserCreate, UserRead

logger = logging.getLogger(__name__)


class AuthService:
    """Регистрация, вход и отзыв refresh-токенов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._tokens = RefreshTokenRepository(session)

    async def register(self, data: UserCreate) -> UserRead:
        """Создать обычного пользователя. Роль из запроса не принимается.

        :param data: email, пароль и имя
        :raises ConflictError: email уже занят
        :return: публичный профиль
        """
        existing = await self._users.get_by_email(data.email)
        if existing is not None:
            raise ConflictError('Email is already registered', code='email_taken')
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=UserRole.USER,
            is_active=True,
        )
        try:
            await self._users.add(user)
        except IntegrityError as exc:
            await self._session.rollback()
            if constraint_name(exc) == 'uq_users_email':
                raise ConflictError('Email is already registered', code='email_taken') from exc
            raise
        return UserRead.model_validate(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        """Проверить пароль и выдать пару токенов.

        :param email: email, регистр не важен
        :param password: пароль
        :raises UnauthorizedError: неверная пара или пользователь отключён
        :return: access и refresh
        """
        user = await self._users.get_by_email(email.strip().lower())
        if user is None:
            verify_password_dummy(password)
            raise UnauthorizedError('Incorrect email or password', code='invalid_credentials')
        password_ok = verify_password(password, user.hashed_password)
        if not password_ok or not user.is_active:
            raise UnauthorizedError('Incorrect email or password', code='invalid_credentials')
        await self._tokens.delete_expired(utcnow())
        return await self._issue_tokens(user)

    async def refresh(self, raw_token: str) -> TokenResponse:
        """Повернуть refresh-токен: старый отзывается, выдаётся новая пара.

        :param raw_token: refresh-токен клиента
        :raises UnauthorizedError: токен неизвестен, отозван или просрочен
        :return: новая пара
        """
        stored = await self._require_active_token(raw_token)
        user = await self._users.get(stored.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError('Refresh token is invalid', code='invalid_refresh_token')
        stored.revoked_at = utcnow()
        return await self._issue_tokens(user)

    async def logout(self, raw_token: str) -> None:
        """Отозвать refresh-токен. Повторный вызов ничего не меняет.

        Access-токен остаётся валидным до своего exp.

        :param raw_token: refresh-токен клиента
        """
        stored = await self._tokens.get_by_hash(hash_token(raw_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = utcnow()

    async def bootstrap_admin(self) -> None:
        """Создать администратора из настроек, если его ещё нет."""
        settings = get_settings()
        await self.bootstrap_admin_user(
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            full_name=settings.bootstrap_admin_full_name,
        )

    async def bootstrap_admin_user(
        self,
        email: str | None,
        password: str | None,
        full_name: str,
    ) -> None:
        """Создать администратора один раз. Повторный вызов пароль не меняет.

        :param email: email администратора
        :param password: исходный пароль
        :param full_name: отображаемое имя
        :raises RuntimeError: email задан, а пароль пуст
        """
        if email is None:
            return
        if password is None:
            raise RuntimeError(
                'BOOTSTRAP_ADMIN_PASSWORD is required when BOOTSTRAP_ADMIN_EMAIL is set',
            )
        payload = UserCreate(email=email, password=password, full_name=full_name)
        existing = await self._users.get_by_email(payload.email)
        if existing is not None:
            logger.info(f'Bootstrap admin already exists: {payload.email}')
            return
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        await self._users.add(user)
        logger.info(f'Bootstrap admin created: {payload.email}')

    async def _require_active_token(self, raw_token: str) -> RefreshToken:
        stored = await self._tokens.get_by_hash(hash_token(raw_token))
        expired = stored is not None and stored.expires_at <= utcnow()
        if stored is None or stored.revoked_at is not None or expired:
            raise UnauthorizedError('Refresh token is invalid', code='invalid_refresh_token')
        return stored

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token, expires_in = create_access_token(user.id)
        raw_refresh = generate_refresh_token()
        settings = get_settings()
        expires_at = utcnow() + timedelta(days=settings.refresh_token_expire_days)
        await self._tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                expires_at=expires_at,
            )
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=expires_in,
        )
