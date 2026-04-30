from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.login_attempt import LoginAttempt


class LoginAttemptRepository:
    """Работает с попытками входа в базе данных."""
    def __init__(self, session: AsyncSession):
        """Сохраняет сессию репозитория."""
        self.session = session

    async def get_by_bucket(self, bucket: str) -> LoginAttempt | None:
        """Ищет попытку входа по ключу."""
        stmt = select(LoginAttempt).where(LoginAttempt.bucket == bucket)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def record_failure(
        self,
        bucket: str,
        now: datetime,
        window_seconds: int,
        max_attempts: int,
        block_seconds: int,
    ) -> LoginAttempt:
        """Обновляет счетчик неудачных входов."""
        attempt = await self.get_by_bucket(bucket)

        if attempt is None:
            attempt = LoginAttempt(
                bucket=bucket,
                failed_attempts=1,
                window_started_at=now,
                blocked_until=None,
                last_attempt_at=now,
            )
            self.session.add(attempt)
        else:
            if attempt.window_started_at + timedelta(
                    seconds=window_seconds) <= now:
                attempt.failed_attempts = 0
                attempt.window_started_at = now
                attempt.blocked_until = None

            attempt.failed_attempts += 1
            attempt.last_attempt_at = now

        if attempt.failed_attempts >= max_attempts:
            attempt.blocked_until = now + timedelta(seconds=block_seconds)

        await self.session.flush()
        return attempt

    async def clear(self, bucket: str) -> None:
        """Сбрасывает счетчик неудачных входов."""
        attempt = await self.get_by_bucket(bucket)
        if attempt is None:
            return

        await self.session.delete(attempt)
        await self.session.flush()
