"""
Unit-тесты для UserRepository.

Проверяем:
- создание пользователя с хэшированием пароля
- поиск пользователя по `id`
- поиск пользователя по `email`
"""

from unittest.mock import MagicMock

from src.core.security import verify_password
from src.repositories.user_repo import UserRepository
from src.schemas.user import UserRegister


def _fake_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


class TestUserRepository:
    async def test_create_user_hashes_password_and_persists_user(self, mock_session):
        repo = UserRepository(mock_session)
        user_data = UserRegister(email="new@example.com", password="Str0ngP@ss!")

        created_user = await repo.create_user(user_data)

        mock_session.add.assert_called_once_with(created_user)
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(created_user)
        assert created_user.email == "new@example.com"
        assert created_user.hashed_password != "Str0ngP@ss!"
        assert verify_password("Str0ngP@ss!", created_user.hashed_password) is True

    async def test_get_user_by_id_returns_user_when_found(self, mock_session, make_user):
        user = make_user(user_id=5, email="found@example.com")
        mock_session.execute.return_value = _fake_result(user)
        repo = UserRepository(mock_session)

        result = await repo.get_user_by_id(5)

        assert result is user

    async def test_get_user_by_email_returns_none_when_user_missing(self, mock_session):
        mock_session.execute.return_value = _fake_result(None)
        repo = UserRepository(mock_session)

        result = await repo.get_user_by_email("missing@example.com")

        assert result is None
