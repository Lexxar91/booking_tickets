from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
 
from src.core.database import get_async_session
from src.schemas.user import UserRead, UserRegister, TokenPair, RefreshTokenRequest
from src.repositories.user_repo import UserRepository
from src.services.auth_service import AuthService
 
 
router = APIRouter(prefix="/auth", tags=["Auth"])
 
 
def get_auth_service(session: AsyncSession = Depends(get_async_session)) -> AuthService:
    return AuthService(UserRepository(session))
 
 
@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
async def register(
    user_in: UserRegister,
    session: AsyncSession = Depends(get_async_session),
    service: AuthService = Depends(get_auth_service),
):
    user = await service.register(user_in)
    await session.commit()
    return user
 
 
@router.post(
    "/login",
    response_model=TokenPair,
    summary="Логин, получение JWT токенов"
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
):
    """
    Принимает username (email) и password через form-data (стандарт OAuth2).
    Возвращает пару токенов: access + refresh.
    """
    return await service.login(
        email=form_data.username,  
        password=form_data.password,
    )
 
 
@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Обновить пару токенов по refresh токену"
)
async def refresh(
    token_request: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    Принимает refresh токен, возвращает новую пару access + refresh.
    Вызывается клиентом автоматически когда access токен протух (401).
    """
    return await service.refresh(token_request.refresh_token)
 