"""
Общие фикстуры для тестов auth_service.

Цели:
- не зависеть от реального `.env`
- не перезагружать модули глобально на всю сессию
- использовать реальные RSA-ключи и реальные модели там, где это полезно
"""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ["DEBUG"] = "false"
os.environ["SQL_ECHO"] = "false"


from src.core.security import hash_password
from src.models.login_attempt import LoginAttempt
from src.models.refresh_token import RefreshToken
from src.models.user import User


@pytest.fixture(scope="session")
def rsa_keys():
    """Генерируем реальную пару RSA-ключей один раз на сессию тестов."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    
    return private_pem, public_pem


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch, rsa_keys):
    """
    Подменяем settings на уровень конкретного теста.

    Такой подход лучше глобального reload:
    - тесты изолированы друг от друга
    - меньше скрытого глобального состояния
    - проще понять, какие настройки реально используются
    """
    import src.core.config
    import src.core.security
    import src.services.auth_service

    private_pem, public_pem = rsa_keys
    fake_settings = SimpleNamespace(
        ALGORITHM="RS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=30,
        JWT_ISSUER="booking-auth-service",
        LOGIN_RATE_LIMIT_MAX_ATTEMPTS=5,
        LOGIN_RATE_LIMIT_WINDOW_SECONDS=300,
        LOGIN_RATE_LIMIT_BLOCK_SECONDS=900,
        jwt_private_key=private_pem,
        jwt_public_key=public_pem,
    )

    monkeypatch.setattr(src.core.config, "settings", fake_settings)
    monkeypatch.setattr(src.core.security, "settings", fake_settings)
    monkeypatch.setattr(src.services.auth_service, "settings", fake_settings)

    return fake_settings


@pytest.fixture()
def mock_session():
    """Минимальный AsyncSession double для repository-тестов."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture()
def make_user():
    """Фабрика реальных объектов User для тестов."""
    cached_hash = None

    def _make(
        user_id: int = 1,
        email: str = "test@example.com",
        password: str | None = None,
        hashed_password: str | None = None,
        role: str = "user",
        is_active: bool = True,
    ) -> User:
        nonlocal cached_hash

        if hashed_password is None:
            if password is not None:
                hashed_password = hash_password(password)
            else:
                if cached_hash is None:
                    cached_hash = hash_password("correct_password")
                hashed_password = cached_hash

        user = User(
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=is_active,
        )
        user.id = user_id
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        return user

    return _make


@pytest.fixture()
def make_login_attempt():
    """Фабрика реальных объектов LoginAttempt для тестов."""

    def _make(
        bucket: str = "127.0.0.1:test@example.com",
        failed_attempts: int = 0,
        window_started_at: datetime | None = None,
        blocked_until: datetime | None = None,
        last_attempt_at: datetime | None = None,
    ) -> LoginAttempt:
        now = datetime.now(timezone.utc)
        return LoginAttempt(
            bucket=bucket,
            failed_attempts=failed_attempts,
            window_started_at=window_started_at or now,
            blocked_until=blocked_until,
            last_attempt_at=last_attempt_at or now,
        )

    return _make


@pytest.fixture()
def make_refresh_token():
    """Фабрика реальных объектов RefreshToken для тестов."""

    def _make(
        user_id: int = 1,
        jti: str | None = None,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            jti=jti or str(uuid4()),
            expires_at=expires_at or (datetime.now(timezone.utc) + timedelta(days=30)),
            revoked_at=revoked_at,
        )
        token.id = 1
        return token

    return _make


@pytest.fixture()
def valid_refresh_token(rsa_keys, make_refresh_token):
    """Возвращает `(token_string, jti, user_id)` для валидного refresh-токена."""
    from jose import jwt

    private_pem, _ = rsa_keys
    token = make_refresh_token()

    payload = {
        "sub": str(token.user_id),
        "role": "user",
        "type": "refresh",
        "jti": token.jti,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
        "iat": datetime.now(timezone.utc),
        "iss": "booking-auth-service",
    }
    token_str = jwt.encode(payload, private_pem, algorithm="RS256")
    return token_str, token.jti, token.user_id


@pytest.fixture()
def valid_access_token(rsa_keys):
    """Возвращает валидный access-токен, подписанный тестовым приватным ключом."""
    from jose import jwt

    private_pem, _ = rsa_keys
    payload = {
        "sub": "1",
        "role": "user",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "iat": datetime.now(timezone.utc),
        "iss": "booking-auth-service",
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")
