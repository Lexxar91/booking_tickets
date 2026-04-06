"""
Unit-тесты для auth dependencies event_service.

Проверяем:
- декодирование валидного access-токена
- 401 для невалидных или неподходящих токенов
- 403 для пользователей без роли admin
"""

import pytest
from fastapi import HTTPException
from jose import JWTError

from src.core.dependencies import get_current_token_payload, require_admin


class TestGetCurrentTokenPayload:
    async def test_returns_payload_for_valid_access_token(self, make_access_token):
        token = make_access_token(sub="15", role="admin", token_type="access")

        payload = await get_current_token_payload(token)

        assert payload.sub == "15"
        assert payload.role == "admin"
        assert payload.type == "access"

    async def test_raises_401_for_invalid_token(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_token_payload("not.a.jwt")

        assert exc_info.value.status_code == 401

    async def test_raises_401_for_wrong_token_type(self, make_access_token):
        refresh_token = make_access_token(sub="15", role="admin", token_type="refresh")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_token_payload(refresh_token)

        assert exc_info.value.status_code == 401

    async def test_raises_401_for_wrong_issuer(self, make_access_token):
        token = make_access_token(sub="15", role="admin", token_type="access", iss="wrong-issuer")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_token_payload(token)

        assert exc_info.value.status_code == 401


class TestRequireAdmin:
    async def test_returns_user_id_for_admin(self, admin_payload):
        result = await require_admin(admin_payload)

        assert result == 1

    async def test_raises_403_for_non_admin(self, user_payload):
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user_payload)

        assert exc_info.value.status_code == 403
