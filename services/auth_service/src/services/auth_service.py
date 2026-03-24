from fastapi import HTTPException, status
from jose import JWTError
 
from src.models.user import User
from src.schemas.user import UserRegister, TokenPair
from src.repositories.user_repo import UserRepository
from src.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def register(self, user_data: UserRegister) -> User:
        """
        Регистрация нового пользователя.
        Проверяем что email не занят — иначе 409 Conflict.
        """

        check_email_in_db = await self.repository.get_user_by_email(user_data.email)
        if check_email_in_db:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует"
            )
        return await self.repository.create_user(user_data)
    
    async def login(self, email: str, password: str) -> TokenPair:
        """
        Логин пользователя.
 
        Важный момент безопасности: мы всегда отвечаем одинаковой ошибкой
        "неверный email или пароль" — неважно что именно неверно.
        Это защита от user enumeration: атакующий не может узнать
        существует ли такой email в системе.
        """
        user = await self.repository.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                  detail="Аккаунт заблокирован"
            )
        return TokenPair(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id, user.role),
        )
    
    async def refresh(self, refresh_token: str) -> TokenPair:
        """
        Обновление пары токенов по refresh токену.
 
        Проверяем:
        1. Токен валидный и не протух (decode_token)
        2. Это именно refresh токен, а не access (type == "refresh")
        3. Пользователь всё ещё существует и активен
        """
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный или протухший токен"
            )
 
        # Защита от подмены: нельзя использовать access токен вместо refresh
        if payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный тип токена"
            )
 
        user = await self.repository.get_user_by_id(int(payload.sub))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или заблокирован"
            )
 
        return TokenPair(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id, user.role),
        )
 