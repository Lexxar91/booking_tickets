"""
Общие фикстуры для тестов booking_service.

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


from src.models.booking import Booking, BookingStatus, EventTickets
from src.schemas.booking import BookingCreate


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
    import src.core.http_client
    import src.core.security

    _, public_pem = rsa_keys
    fake_settings = SimpleNamespace(
        APP_TITLE="Booking Service",
        DEBUG=False,
        SQL_ECHO=False,
        ALGORITHM="RS256",
        JWT_ISSUER="booking-auth-service",
        EVENT_SERVICE_URL="http://event_service:8000",
        jwt_public_key=public_pem,
    )

    monkeypatch.setattr(src.core.config, "settings", fake_settings)
    monkeypatch.setattr(src.core.dependencies, "decode_token", src.core.security.decode_token)
    monkeypatch.setattr(src.core.http_client, "settings", fake_settings)
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
def make_booking():
    """Фабрика реальных объектов Booking."""

    def _make(
        booking_id: int = 1,
        user_id: int = 1,
        event_id: int = 1,
        status: BookingStatus = BookingStatus.CONFIRMED,
        price_at_booking: Decimal = Decimal("1000.00"),
    ) -> Booking:
        booking = Booking(
            user_id=user_id,
            event_id=event_id,
            status=status,
            price_at_booking=price_at_booking,
        )
        booking.id = booking_id
        booking.created_at = datetime.now(timezone.utc)
        booking.updated_at = datetime.now(timezone.utc)
        return booking

    return _make


@pytest.fixture()
def make_event_tickets():
    """Фабрика реальных объектов EventTickets."""

    def _make(event_id: int = 1, available_tickets: int = 10) -> EventTickets:
        return EventTickets(event_id=event_id, available_tickets=available_tickets)

    return _make


@pytest.fixture()
def booking_create_data() -> BookingCreate:
    """Готовые входные данные для создания бронирования."""
    return BookingCreate(event_id=1, user_email="user@example.com")


@pytest.fixture()
def make_access_token(rsa_keys):
    """Фабрика валидных access JWT для dependency-тестов."""

    def _make(
        sub: str = "1",
        role: str = "user",
        token_type: str = "access",
        iss: str = "booking-auth-service",
    ) -> str:
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
