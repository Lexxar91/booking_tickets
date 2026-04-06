"""
Общие фикстуры для тестов event_service.

Цели:
- не зависеть от реального `.env`
- использовать реальные RSA-ключи там, где это полезно
- изолировать unit-тесты от локальной БД и внешней инфраструктуры
"""

import os
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt


os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ["DEBUG"] = "false"
os.environ["SQL_ECHO"] = "false"


from src.models.event import Event
from src.schemas.auth import TokenPayload
from src.schemas.event import EventCreate, EventUpdate


@pytest.fixture(scope="session")
def rsa_keys():
    """Генерируем RSA-пару один раз на сессию тестов."""
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

    Такой подход держит unit-тесты изолированными и не тащит в них
    локальные переменные окружения или compose/k8s-конфигурацию.
    """
    import src.core.config
    import src.core.dependencies
    import src.core.security

    _, public_pem = rsa_keys
    fake_settings = SimpleNamespace(
        APP_TITLE="Event Service",
        DEBUG=False,
        SQL_ECHO=False,
        ALGORITHM="RS256",
        JWT_ISSUER="booking-auth-service",
        jwt_public_key=public_pem,
    )

    monkeypatch.setattr(src.core.config, "settings", fake_settings)
    monkeypatch.setattr(src.core.dependencies, "decode_token", src.core.security.decode_token)
    monkeypatch.setattr(src.core.security, "settings", fake_settings)

    return fake_settings


@pytest.fixture()
def mock_session():
    """Минимальный AsyncSession double для unit-тестов."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture()
def make_event():
    """Фабрика реальных объектов Event."""

    def _make(
        event_id: int = 1,
        title: str = "Concert",
        description: str | None = "Big live show",
        price: Decimal = Decimal("1500.00"),
        total_tickets: int = 100,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
    ) -> Event:
        start = date_start or datetime(2026, 4, 20, 18, 0, tzinfo=timezone.utc)
        end = date_end or datetime(2026, 4, 20, 21, 0, tzinfo=timezone.utc)

        event = Event(
            title=title,
            description=description,
            price=price,
            total_tickets=total_tickets,
            date_start=start,
            date_end=end,
        )
        event.id = event_id
        event.created_at = datetime.now(timezone.utc)
        event.updated_at = datetime.now(timezone.utc)
        return event

    return _make


@pytest.fixture()
def event_create_data() -> EventCreate:
    """Готовые входные данные для создания мероприятия."""
    return EventCreate(
        title="Concert",
        description="Big live show",
        price=Decimal("1500.00"),
        total_tickets=100,
        date_start=datetime(2026, 4, 20, 18, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 4, 20, 21, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def event_update_data() -> EventUpdate:
    """Готовые входные данные для обновления мероприятия."""
    return EventUpdate(title="Updated concert", price=Decimal("2000.00"))


@pytest.fixture()
def make_access_token(rsa_keys):
    """Фабрика валидных access JWT для dependency-тестов."""

    def _make(sub: str = "1", role: str = "user", token_type: str = "access", iss: str = "booking-auth-service"):
        private_pem, _ = rsa_keys
        payload = {
            "sub": sub,
            "role": role,
            "type": token_type,
            "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
            "iat": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "iss": iss,
        }
        return jwt.encode(payload, private_pem, algorithm="RS256")

    return _make


@pytest.fixture()
def admin_payload() -> TokenPayload:
    return TokenPayload(
        sub="1",
        role="admin",
        type="access",
        exp=datetime(2099, 1, 1, tzinfo=timezone.utc),
        iss="booking-auth-service",
    )


@pytest.fixture()
def user_payload() -> TokenPayload:
    return TokenPayload(
        sub="2",
        role="user",
        type="access",
        exp=datetime(2099, 1, 1, tzinfo=timezone.utc),
        iss="booking-auth-service",
    )
