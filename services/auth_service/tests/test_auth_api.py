"""
API-тесты для роутов auth_service.

Проверяем:
- wiring роутов и dependency overrides
- commit/response поведение
- передачу данных из HTTP слоя в AuthService
"""

from unittest.mock import AsyncMock, create_autospec

import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.requests import Request

from src.api.v1.auth import login, logout, refresh, register
from src.schemas.user import (
    LogoutRequest,
    RefreshTokenRequest,
    TokenPair,
    UserRegister,
)
from src.services.auth_service import AuthService


def _build_request(
    *,
    headers: dict[str, str] | None = None,
    client_host: str = "127.0.0.1",
) -> Request:
    """Собирает тестовый HTTP-запрос."""
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


class TestAuthApi:
    """Тесты API авторизации."""
    async def test_register_returns_created_user_and_commits(self, make_user):
        """Проверяет успешный сценарий с commit."""
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(AuthService, instance=True)
        service.register.return_value = make_user(
            user_id=11, email="new@example.com")

        result = await register(
            user_in=UserRegister(email="new@example.com",
                                 password="Str0ngP@ss!"),
            session=session,
            service=service,
        )

        assert result.email == "new@example.com"
        session.commit.assert_awaited_once()
        user_in = service.register.await_args.args[0]
        assert user_in.email == "new@example.com"
        assert user_in.password == "Str0ngP@ss!"

    async def test_login_uses_forwarded_ip_and_returns_token_pair(self):
        """Проверяет ожидаемый результат."""
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(AuthService, instance=True)
        service.login.return_value = TokenPair(
            access_token="access-token",
            refresh_token="refresh-token",
        )

        result = await login(
            request=_build_request(
                headers={"x-forwarded-for": "203.0.113.10, 10.0.0.5"}),
            form_data=OAuth2PasswordRequestForm(
                username="user@example.com",
                password="secret123",
                scope="",
            ),
            session=session,
            service=service,
        )

        assert result.access_token == "access-token"
        session.commit.assert_awaited_once()
        assert service.login.await_args.kwargs == {
            "email": "user@example.com",
            "password": "secret123",
            "client_ip": "203.0.113.10",
        }

    async def test_login_commits_even_when_service_raises_http_exception(self):
        """Проверяет сценарий с ошибкой."""
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(AuthService, instance=True)
        service.login.side_effect = HTTPException(
            status_code=401, detail="Неверный email или пароль")

        with pytest.raises(HTTPException) as exc_info:
            await login(
                request=_build_request(client_host="198.51.100.5"),
                form_data=OAuth2PasswordRequestForm(
                    username="user@example.com",
                    password="wrong-password",
                    scope="",
                ),
                session=session,
                service=service,
            )

        assert exc_info.value.status_code == 401
        session.commit.assert_awaited_once()

    async def test_refresh_commits_and_returns_new_token_pair(self):
        """Проверяет успешный сценарий с commit."""
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(AuthService, instance=True)
        service.refresh.return_value = TokenPair(
            access_token="new-access",
            refresh_token="new-refresh",
        )

        result = await refresh(
            token_request=RefreshTokenRequest(refresh_token="refresh-token"),
            session=session,
            service=service,
        )

        assert result.refresh_token == "new-refresh"
        service.refresh.assert_awaited_once_with("refresh-token")
        session.commit.assert_awaited_once()

    async def test_logout_returns_204_and_commits(self):
        """Проверяет успешный сценарий с commit."""
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(AuthService, instance=True)

        result = await logout(
            token_request=LogoutRequest(refresh_token="refresh-token"),
            session=session,
            service=service,
        )

        assert result is None
        service.logout.assert_awaited_once_with("refresh-token")
        session.commit.assert_awaited_once()
