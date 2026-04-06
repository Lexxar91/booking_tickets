"""
Unit-тесты для LoginAttemptRepository.

Проверяем:
- поиск bucket в хранилище
- обновление состояния rate limit окна
- блокировку после превышения лимита
- очистку состояния после успешного логина
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.repositories.login_attempt_repo import LoginAttemptRepository


def _fake_result(scalar_value):
    """Обёртка над mock результата session.execute()."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_value)
    return result


class TestLoginAttemptRepository:
    """Тестируем репозиторий на уровне поведения, без реальной БД."""

    async def test_get_by_bucket_returns_none(self, mock_session):
        mock_session.execute.return_value = _fake_result(None)
        repo = LoginAttemptRepository(mock_session)
        result = await repo.get_by_bucket("127.0.0.1:test@test.com")
        assert result is None

    async def test_get_by_bucket_returns_attempt(self, mock_session, make_login_attempt):
        attempt = make_login_attempt()
        mock_session.execute.return_value = _fake_result(attempt)
        repo = LoginAttemptRepository(mock_session)
        result = await repo.get_by_bucket("127.0.0.1:test@test.com")
        assert result is attempt

    async def test_record_failure_first_attempt(self, mock_session):
        """Первая попытка — создаём новую запись с failed_attempts=1."""
        mock_session.execute.return_value = _fake_result(None)
        repo = LoginAttemptRepository(mock_session)
        now = datetime.now(timezone.utc)

        result = await repo.record_failure(
            bucket="127.0.0.1:test@test.com",
            now=now,
            window_seconds=300,
            max_attempts=5,
            block_seconds=900,
        )

        assert result.failed_attempts == 1
        assert result.blocked_until is None
        mock_session.add.assert_called_once()

    async def test_record_failure_blocks_after_max_attempts(self, mock_session, make_login_attempt):
        """После 5 попыток в пределах окна — blocked_until установлен."""
        now = datetime.now(timezone.utc)
        attempt = make_login_attempt(
            failed_attempts=4,
            window_started_at=now - timedelta(seconds=60),
        )
        mock_session.execute.return_value = _fake_result(attempt)
        repo = LoginAttemptRepository(mock_session)

        result = await repo.record_failure(
            bucket="127.0.0.1:test@test.com",
            now=now,
            window_seconds=300,
            max_attempts=5,
            block_seconds=900,
        )

        assert result.failed_attempts == 5
        assert result.blocked_until == now + timedelta(seconds=900)

    async def test_record_failure_window_resets(self, mock_session, make_login_attempt):
        """Если окно истекло — счётчик сбрасывается до 1."""
        now = datetime.now(timezone.utc)
        old_attempt = make_login_attempt(
            failed_attempts=4,
            window_started_at=now - timedelta(seconds=600),  # окно 300с истекло
        )
        mock_session.execute.return_value = _fake_result(old_attempt)
        repo = LoginAttemptRepository(mock_session)

        result = await repo.record_failure(
            bucket="127.0.0.1:test@test.com",
            now=now,
            window_seconds=300,
            max_attempts=5,
            block_seconds=900,
        )

        # Окно истекло → сброс → 1 новая попытка
        assert result.failed_attempts == 1
        assert result.blocked_until is None

    async def test_clear_deletes_attempt(self, mock_session, make_login_attempt):
        """clear() удаляет запись из БД."""
        attempt = make_login_attempt()
        mock_session.execute.return_value = _fake_result(attempt)
        repo = LoginAttemptRepository(mock_session)

        await repo.clear("127.0.0.1:test@test.com")

        mock_session.delete.assert_called_once_with(attempt)
        mock_session.flush.assert_awaited_once()

    async def test_clear_noop_when_bucket_not_found(self, mock_session):
        """clear() не падает если записи нет."""
        mock_session.execute.return_value = _fake_result(None)
        repo = LoginAttemptRepository(mock_session)

        await repo.clear("127.0.0.1:test@test.com")

        mock_session.delete.assert_not_called()
