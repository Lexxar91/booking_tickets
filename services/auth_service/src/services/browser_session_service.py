"""Управление сессиями BFF без передачи JWT браузеру."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import compare_digest, token_urlsafe

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.security import decode_token
from src.models.browser_session import BrowserSession
from src.repositories.browser_session_repo import BrowserSessionRepository
from src.schemas.user import TokenPair, UserRead
from src.services.auth_service import AuthService

COOKIE_NAME = "__Host-booking_session"


class BrowserSessionService:
    """Шифрует JWT и обновляет их в общей с AuthService транзакции."""

    def __init__(self, session: AsyncSession, auth: AuthService) -> None:
        """Сохраняет зависимости; фиксацией транзакции управляет API."""
        self.session = session
        self.auth = auth
        self.repository = BrowserSessionRepository(session)

    @staticmethod
    def cipher() -> Fernet:
        """Возвращает шифратор или запрещает вход без серверного ключа."""
        if not settings.BFF_SESSION_KEY:
            raise HTTPException(503, "BFF_SESSION_KEY не настроен")
        return Fernet(settings.BFF_SESSION_KEY.get_secret_value().encode())

    def store_tokens(self, browser: BrowserSession, pair: TokenPair) -> None:
        """Шифрует пару и сохраняет срок действия access-токена."""
        cipher = self.cipher()
        browser.access_token = cipher.encrypt(
            pair.access_token.encode()).decode()
        browser.refresh_token = cipher.encrypt(
            pair.refresh_token.encode()).decode()
        browser.access_expires_at = decode_token(pair.access_token).exp

    def decrypt(self, value: str) -> str:
        """Расшифровывает токен; поврежденная сессия требует нового входа."""
        try:
            return self.cipher().decrypt(value.encode()).decode()
        except InvalidToken:
            raise HTTPException(401, "Сессия недействительна") from None

    async def create(
        self, email: str, password: str, client_ip: str,
    ) -> tuple[str, BrowserSession]:
        """Создает случайный идентификатор и серверную запись сессии."""
        self.cipher()
        pair = await self.auth.login(email, password, client_ip)
        session_id = token_urlsafe(32)
        browser = BrowserSession(
            id_hash=sha256(session_id.encode()).hexdigest(),
            user_id=int(decode_token(pair.access_token).sub),
            csrf_token=token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.store_tokens(browser, pair)
        self.session.add(browser)
        return session_id, browser

    async def get(
        self, session_id: str | None, csrf_token: str | None = None,
        require_csrf: bool = False,
    ) -> BrowserSession:
        """Проверяет сессию и CSRF под блокировкой строки в БД."""
        if not session_id or len(session_id) != 43:
            raise HTTPException(401, "Требуется вход")
        browser = await self.repository.get_locked(session_id)
        if browser is None or browser.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(401, "Сессия истекла или отозвана")
        if require_csrf and not compare_digest(
            (csrf_token or "").encode(), browser.csrf_token.encode(),
        ):
            raise HTTPException(403, "Неверный CSRF-токен")
        return browser

    async def refresh(
        self, browser: BrowserSession, force: bool = False,
    ) -> None:
        """Обновляет JWT до истечения access-токена под блокировкой сессии."""
        if force or browser.access_expires_at <= (
            datetime.now(timezone.utc) + timedelta(seconds=30)
        ):
            pair = await self.auth.refresh(self.decrypt(browser.refresh_token))
            self.store_tokens(browser, pair)

    async def public_data(self, browser: BrowserSession) -> dict[str, object]:
        """Возвращает только пользователя и CSRF-токен без JWT."""
        user = await self.auth.repository.get_user_by_id(browser.user_id)
        if user is None or not user.is_active:
            raise HTTPException(401, "Пользователь недоступен")
        return {"user": UserRead.model_validate(user).model_dump(mode="json"),
                "csrf_token": browser.csrf_token}

    async def revoke(self, browser: BrowserSession) -> None:
        """Отзывает refresh-токен и удаляет браузерную сессию."""
        try:
            await self.auth.logout(self.decrypt(browser.refresh_token))
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
        await self.session.delete(browser)
