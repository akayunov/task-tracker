from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from tasktracker.api.deps import CurrentUser, DbSession
from tasktracker.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from tasktracker.schemas.user import UserCreate, UserRead
from tasktracker.services.auth import AuthService

router = APIRouter()


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, session: DbSession) -> UserRead:
    """Зарегистрировать пользователя."""
    return await AuthService(session).register(payload)


@router.post('/login')
async def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    """Войти по email и паролю и получить пару токенов."""
    return await AuthService(session).login(payload.email, payload.password)


@router.post('/token')
async def issue_token(
    session: DbSession,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """OAuth2-форма для кнопки Authorize в Swagger. username — это email."""
    return await AuthService(session).login(form.username, form.password)


@router.post('/refresh')
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenResponse:
    """Обменять refresh-токен на новую пару. Старый refresh перестаёт работать."""
    return await AuthService(session).refresh(payload.refresh_token)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(payload: LogoutRequest, session: DbSession) -> Response:
    """Отозвать refresh-токен. Access-токен действует до истечения срока."""
    await AuthService(session).logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/me')
async def me(actor: CurrentUser) -> UserRead:
    """Текущий пользователь."""
    return UserRead.model_validate(actor)
