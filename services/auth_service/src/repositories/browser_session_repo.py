"""Доступ к серверным браузерным сессиям."""

from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.browser_session import BrowserSession


class BrowserSessionRepository:
    """Блокирует сессию для последовательной ротации токенов."""

    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию БД; commit выполняет обработчик BFF."""
        self.session = session

    async def get_locked(self, session_id: str) -> BrowserSession | None:
        """Читает актуальную сессию под блокировкой до commit/rollback."""
        id_hash = sha256(session_id.encode()).hexdigest()
        statement = (
            select(BrowserSession)
            .where(BrowserSession.id_hash == id_hash)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
