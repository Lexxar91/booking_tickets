"""
Unit-тесты для AuthService.

Подход:
- тестируем поведение сервисного слоя
- зависимости сервиса мокируются на уровне репозиториев
- не привязываемся к внутреннему устройству SQLAlchemy-сессии
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, create_autospec

import pytest
from fastapi import HTTPException
from jose import jwt

from src.repositories.login_attempt_repo import LoginAttemptRepository
from src.repositories.refresh_token_repo import RefreshTokenRepository
from src.repositories.user_repo import UserRepository
from src.schemas.user import UserRegister
from src.services.auth_service import AuthService


def _build_auth_service(
    user_repo: UserRepository | None = None,
    refresh_token_repo: RefreshTokenRepository | None = None,
    login_attempt_repo: LoginAttemptRepository | None = None,
) -> tuple[
    AuthService,
    UserRepository,
    RefreshTokenRepository,
    LoginAttemptRepository,
]:
    """Собирает сервис и зависимости для теста."""
    user_repo = user_repo or create_autospec(UserRepository, instance=True)
    refresh_token_repo = refresh_token_repo or create_autospec(
        RefreshTokenRepository, instance=True)
    login_attempt_repo = login_attempt_repo or create_autospec(
        LoginAttemptRepository, instance=True)

    service = AuthService(
        repository=user_repo,
        refresh_token_repository=refresh_token_repo,
        login_attempt_repository=login_attempt_repo,
    )
    return service, user_repo, refresh_token_repo, login_attempt_repo


class TestAuthServiceRegister:
    """Тесты регистрации в AuthService."""
    async def test_register_success(self, make_user):
        """Проверяет рабочий сценарий."""
        service, user_repo, _, _ = _build_auth_service()
        user_data = UserRegister(
            email="new@example.com", password="Str0ngP@ss!")
        new_user = make_user(email="new@example.com")

        user_repo.get_user_by_email.return_value = None
        user_repo.create_user.return_value = new_user

        result = await service.register(user_data)

        assert result is new_user
        user_repo.get_user_by_email.assert_awaited_once_with("new@example.com")
        user_repo.create_user.assert_awaited_once_with(user_data)

    async def test_register_duplicate_email(self, make_user):
        """Проверяет рабочий сценарий."""
        service, user_repo, _, _ = _build_auth_service()
        user_data = UserRegister(
            email="existing@example.com", password="Str0ngP@ss!")
        user_repo.get_user_by_email.return_value = make_user(
            email="existing@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await service.register(user_data)

        assert exc_info.value.status_code == 409
        user_repo.create_user.assert_not_called()


class TestAuthServiceLogin:
    """Тесты входа в AuthService."""
    async def test_login_success(self, make_user, make_refresh_token):
        """Проверяет рабочий сценарий."""
        (
            service,
            user_repo,
            refresh_token_repo,
            login_attempt_repo,
        ) = _build_auth_service()
        user = make_user(
            email="test@example.com",
            role="admin",
            password="correct_password",
        )

        user_repo.get_user_by_email.return_value = user
        login_attempt_repo.get_by_bucket.return_value = None
        refresh_token_repo.create_token.return_value = make_refresh_token(
            user_id=user.id)

        result = await service.login(
            "test@example.com",
            "correct_password",
            "127.0.0.1",
        )

        assert result.access_token
        assert result.refresh_token
        login_attempt_repo.clear.assert_awaited_once_with(
            "127.0.0.1:test@example.com")
        refresh_token_repo.create_token.assert_awaited_once()

        kwargs = refresh_token_repo.create_token.await_args.kwargs
        assert kwargs["user_id"] == user.id
        assert isinstance(kwargs["jti"], str)
        assert kwargs["expires_at"] > datetime.now(timezone.utc)

    async def test_login_wrong_password(self, make_user, make_login_attempt):
        """Проверяет рабочий сценарий."""
        (
            service,
            user_repo,
            refresh_token_repo,
            login_attempt_repo,
        ) = _build_auth_service()
        user_repo.get_user_by_email.return_value = make_user(
            email="test@example.com",
            password="correct_password",
        )
        login_attempt_repo.get_by_bucket.return_value = None
        login_attempt_repo.record_failure.return_value = make_login_attempt()

        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                "test@example.com",
                "wrong_password",
                "127.0.0.1",
            )

        assert exc_info.value.status_code == 401
        login_attempt_repo.record_failure.assert_awaited_once()
        login_attempt_repo.clear.assert_not_called()
        refresh_token_repo.create_token.assert_not_called()

    async def test_login_inactive_user(self, make_user):
        """Проверяет рабочий сценарий."""
        (
            service,
            user_repo,
            refresh_token_repo,
            login_attempt_repo,
        ) = _build_auth_service()
        user_repo.get_user_by_email.return_value = make_user(
            email="blocked@example.com",
            is_active=False,
            password="correct_password",
        )
        login_attempt_repo.get_by_bucket.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                "blocked@example.com",
                "correct_password",
                "127.0.0.1",
            )

        assert exc_info.value.status_code == 403
        login_attempt_repo.clear.assert_not_called()
        refresh_token_repo.create_token.assert_not_called()

    async def test_login_rate_limited(self, make_login_attempt):
        """Проверяет рабочий сценарий."""
        service, user_repo, _, login_attempt_repo = _build_auth_service()
        now = datetime.now(timezone.utc)
        login_attempt_repo.get_by_bucket.return_value = make_login_attempt(
            bucket="127.0.0.1:test@example.com",
            blocked_until=now + timedelta(seconds=600),
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                "test@example.com",
                "any_password",
                "127.0.0.1",
            )

        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers
        user_repo.get_user_by_email.assert_not_called()

    async def test_login_rate_limit_triggers_after_max_failures(
            self, make_login_attempt):
        """Проверяет рабочий сценарий."""
        service, user_repo, _, login_attempt_repo = _build_auth_service()
        now = datetime.now(timezone.utc)

        user_repo.get_user_by_email.return_value = None
        login_attempt_repo.get_by_bucket.return_value = None
        login_attempt_repo.record_failure.return_value = make_login_attempt(
            failed_attempts=5,
            blocked_until=now + timedelta(seconds=900),
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.login("test@example.com", "wrong", "127.0.0.1")

        assert exc_info.value.status_code == 429


class TestAuthServiceRefresh:
    """Тесты обновления токенов в AuthService."""
    async def test_refresh_success(
            self,
            make_user,
            make_refresh_token,
            valid_refresh_token):
        """Проверяет рабочий сценарий."""
        token_str, jti, user_id = valid_refresh_token
        service, user_repo, refresh_token_repo, _ = _build_auth_service()

        stored_token = make_refresh_token(user_id=user_id, jti=jti)
        user_repo.get_user_by_id.return_value = make_user(
            user_id=user_id, role="user")
        refresh_token_repo.get_active_token.return_value = stored_token
        refresh_token_repo.create_token.return_value = make_refresh_token(
            user_id=user_id)

        result = await service.refresh(token_str)

        assert result.access_token
        assert result.refresh_token
        refresh_token_repo.get_active_token.assert_awaited_once_with(
            user_id=user_id,
            jti=jti,
            now=ANY,
        )
        refresh_token_repo.revoke.assert_awaited_once_with(
            stored_token, revoked_at=ANY)
        refresh_token_repo.create_token.assert_awaited_once()

    async def test_refresh_revoked_token_raises_401(self, valid_refresh_token):
        """Проверяет ошибку 401."""
        token_str, jti, user_id = valid_refresh_token
        service, user_repo, refresh_token_repo, _ = _build_auth_service()
        refresh_token_repo.get_active_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.refresh(token_str)

        assert exc_info.value.status_code == 401
        refresh_token_repo.get_active_token.assert_awaited_once_with(
            user_id=user_id,
            jti=jti,
            now=ANY,
        )
        user_repo.get_user_by_id.assert_not_called()

    async def test_refresh_wrong_token_type_raises_401(
            self, valid_access_token):
        """Проверяет ошибку 401."""
        service, _, _, _ = _build_auth_service()

        with pytest.raises(HTTPException) as exc_info:
            await service.refresh(valid_access_token)

        assert exc_info.value.status_code == 401

    async def test_refresh_expired_token_raises_401(self, rsa_keys):
        """Проверяет ошибку 401."""
        private_pem, _ = rsa_keys
        expired_payload = {
            "sub": "1",
            "role": "user",
            "type": "refresh",
            "jti": "some-jti",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=10),
            "iat": datetime.now(timezone.utc) - timedelta(hours=1),
            "iss": "booking-auth-service",
        }
        expired_token = jwt.encode(
            expired_payload, private_pem, algorithm="RS256")
        service, _, _, _ = _build_auth_service()

        with pytest.raises(HTTPException) as exc_info:
            await service.refresh(expired_token)

        assert exc_info.value.status_code == 401


class TestAuthServiceLogout:
    """Тесты выхода в AuthService."""
    async def test_logout_success(
            self,
            valid_refresh_token,
            make_refresh_token):
        """Проверяет рабочий сценарий."""
        token_str, jti, user_id = valid_refresh_token
        service, _, refresh_token_repo, _ = _build_auth_service()
        stored_token = make_refresh_token(user_id=user_id, jti=jti)
        refresh_token_repo.get_active_token.return_value = stored_token

        await service.logout(token_str)

        refresh_token_repo.get_active_token.assert_awaited_once_with(
            user_id=user_id,
            jti=jti,
            now=ANY,
        )
        refresh_token_repo.revoke.assert_awaited_once_with(
            stored_token, revoked_at=ANY)

    async def test_logout_already_revoked_raises_401(
            self, valid_refresh_token):
        """Проверяет ошибку 401."""
        token_str, jti, user_id = valid_refresh_token
        service, _, refresh_token_repo, _ = _build_auth_service()
        refresh_token_repo.get_active_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.logout(token_str)

        assert exc_info.value.status_code == 401
        refresh_token_repo.get_active_token.assert_awaited_once_with(
            user_id=user_id,
            jti=jti,
            now=ANY,
        )
