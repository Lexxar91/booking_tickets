"""
Unit-тесты для auth dependencies booking_service.

Проверяем:
- извлечение `user_id` из валидного access-токена
- 401 для невалидного токена
- 401 для refresh-токена вместо access-токена
"""

import pytest
from fastapi import HTTPException

from src.core.dependencies import get_current_user_id


class TestGetCurrentUserId:
    """Тесты извлечения пользователя из токена."""
    async def test_returns_user_id_for_valid_access_token(
            self, make_access_token):
        """Проверяет ожидаемый результат."""
        token = make_access_token(sub="15", role="user", token_type="access")

        user_id = await get_current_user_id(token)

        assert user_id == 15

    async def test_raises_401_for_invalid_token(self):
        """Проверяет ошибку 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id("not.a.jwt")

        assert exc_info.value.status_code == 401

    async def test_raises_401_for_wrong_token_type(self, make_access_token):
        """Проверяет ошибку 401."""
        refresh_token = make_access_token(
            sub="15", role="user", token_type="refresh")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(refresh_token)

        assert exc_info.value.status_code == 401
