import hashlib
import secrets
from datetime import timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from tasktracker.core.config import get_settings
from tasktracker.core.exceptions import UnauthorizedError
from tasktracker.core.time import utcnow

_password_hash = PasswordHash.recommended()
# Verification cost stays constant when the account does not exist.
_DUMMY_PASSWORD_HASH = _password_hash.hash('not-a-real-password')


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def verify_password_dummy(password: str) -> None:
    _password_hash.verify(password, _DUMMY_PASSWORD_HASH)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    now = utcnow()
    payload = {
        'sub': str(user_id),
        'type': 'access',
        'iat': int(now.timestamp()),
        'exp': now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError('Invalid access token', code='invalid_access_token') from exc
    if payload.get('type') != 'access':
        raise UnauthorizedError('Invalid access token', code='invalid_access_token')
    subject = payload.get('sub')
    try:
        return UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError('Invalid access token', code='invalid_access_token') from exc
