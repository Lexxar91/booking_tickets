from datetime import datetime, timezone

from fastapi import HTTPException, status

from src.core.config import settings
from src.core.metrics import (
    decrement_active_sessions,
    increment_active_sessions,
    track_login_attempt,
    track_logout,
    track_registration,
    track_token_refresh,
)
from src.core.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from src.models.user import User
from src.repositories.login_attempt_repo import LoginAttemptRepository
from src.repositories.refresh_token_repo import RefreshTokenRepository
from src.repositories.user_repo import UserRepository
from src.schemas.user import TokenPair, UserRegister


class AuthService:
    """Содержит бизнес-логику авторизации."""
    def __init__(
        self,
        repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        login_attempt_repository: LoginAttemptRepository,
    ):
        """Сохраняет зависимости сервиса."""
        self.repository = repository
        self.refresh_token_repository = refresh_token_repository
        self.login_attempt_repository = login_attempt_repository

    @staticmethod
    def _now() -> datetime:
        """Возвращает текущее время в UTC."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _login_bucket(email: str, client_ip: str) -> str:
        """Собирает ключ для ограничения попыток входа."""
        return f"{client_ip}:{email.strip().lower()}"

    async def register(self, user_data: UserRegister) -> User:
        """Регистрирует нового пользователя."""
        check_email_in_db = await self.repository.get_user_by_email(
            user_data.email
        )
        if check_email_in_db:
            track_registration(status="duplicate")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует",
            )
        track_registration(status="success")
        return await self.repository.create_user(user_data)

    async def login(
        self,
        email: str,
        password: str,
        client_ip: str,
    ) -> TokenPair:
        """Выполняет вход пользователя."""
        now = self._now()
        bucket = self._login_bucket(email=email, client_ip=client_ip)
        attempt = await self.login_attempt_repository.get_by_bucket(bucket)

        if attempt and attempt.blocked_until and attempt.blocked_until > now:
            track_login_attempt(status="rate_limited")
            retry_after = max(
                1, int((attempt.blocked_until - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много попыток входа. Попробуйте позже.",
                headers={"Retry-After": str(retry_after)},
            )

        user = await self.repository.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            track_login_attempt(status="failure")
            failed_attempt = (
                await self.login_attempt_repository.record_failure(
                    bucket=bucket,
                    now=now,
                    window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
                    max_attempts=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
                    block_seconds=settings.LOGIN_RATE_LIMIT_BLOCK_SECONDS,
                )
            )
            if (
                failed_attempt.blocked_until
                and failed_attempt.blocked_until > now
            ):
                retry_after = max(
                    1,
                    int((failed_attempt.blocked_until - now).total_seconds()),
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Слишком много попыток входа. Попробуйте позже.",
                    headers={"Retry-After": str(retry_after)},
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
            )

        if not user.is_active:
            track_login_attempt(status="failure")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт заблокирован",
            )

        await self.login_attempt_repository.clear(bucket)
        refresh_token, jti, expires_at = create_refresh_token(
            user.id,
            user.role,
        )
        await self.refresh_token_repository.create_token(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
        )

        track_login_attempt(status="success")
        increment_active_sessions()

        return TokenPair(
            access_token=create_access_token(user.id, user.role),
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Обновляет пару токенов."""
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            track_token_refresh(status="invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный или протухший токен",
            )

        if payload.type != "refresh" or payload.jti is None:
            track_token_refresh(status="invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный тип токена",
            )

        user_id = int(payload.sub)
        now = self._now()
        stored_token = await self.refresh_token_repository.get_active_token(
            user_id=user_id,
            jti=payload.jti,
            now=now,
        )
        if stored_token is None:
            track_token_refresh(status="revoked")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh токен отозван или истёк",
            )

        user = await self.repository.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или заблокирован",
            )

        await self.refresh_token_repository.revoke(
            stored_token,
            revoked_at=now,
        )
        new_refresh_token, new_jti, expires_at = create_refresh_token(
            user.id,
            user.role,
        )
        await self.refresh_token_repository.create_token(
            user_id=user.id,
            jti=new_jti,
            expires_at=expires_at,
        )

        track_token_refresh(status="success")

        return TokenPair(
            access_token=create_access_token(user.id, user.role),
            refresh_token=new_refresh_token,
        )

    async def logout(self, refresh_token: str) -> None:
        """Отзывает refresh-токен."""
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            track_logout(status="not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный или протухший токен",
            )

        if payload.type != "refresh" or payload.jti is None:
            track_logout(status="not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный тип токена",
            )

        token = await self.refresh_token_repository.get_active_token(
            user_id=int(payload.sub),
            jti=payload.jti,
            now=self._now(),
        )
        if token is None:
            track_logout(status="not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh токен уже отозван или истёк",
            )

        await self.refresh_token_repository.revoke(
            token,
            revoked_at=self._now(),
        )
        track_logout(status="success")
        decrement_active_sessions()
