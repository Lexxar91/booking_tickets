from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_session
from src.repositories.login_attempt_repo import LoginAttemptRepository
from src.repositories.refresh_token_repo import RefreshTokenRepository
from src.repositories.user_repo import UserRepository
from src.schemas.user import (LogoutRequest, RefreshTokenRequest, TokenPair,
                              UserRead, UserRegister)
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
) -> AuthService:
    """Собирает сервис авторизации."""
    return AuthService(
        repository=UserRepository(session),
        refresh_token_repository=RefreshTokenRepository(session),
        login_attempt_repository=LoginAttemptRepository(session),
    )


def _get_client_ip(request: Request) -> str:
    """Извлекает IP клиента из запроса."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
async def register(
    user_in: UserRegister,
    session: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    """Обрабатывает регистрацию пользователя."""
    user = await service.register(user_in)
    await session.commit()
    return user


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Логин, получение JWT токенов",
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    """Обрабатывает вход пользователя."""
    try:
        token_pair = await service.login(
            email=form_data.username,
            password=form_data.password,
            client_ip=_get_client_ip(request),
        )
        await session.commit()
        return token_pair
    except HTTPException:
        await session.commit()
        raise


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Обновить пару токенов по refresh токену",
)
async def refresh(
    token_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    """Обрабатывает обновление токенов."""
    token_pair = await service.refresh(token_request.refresh_token)
    await session.commit()
    return token_pair


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать refresh токен",
)
async def logout(
    token_request: LogoutRequest,
    session: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    """Обрабатывает выход пользователя."""
    await service.logout(token_request.refresh_token)
    await session.commit()
