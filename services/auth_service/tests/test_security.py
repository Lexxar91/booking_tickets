"""
Тесты для security.py — JWT token lifecycle.

Проверяем:
- Создание и декодирование access-токена
- Создание и декодирование refresh-токена (с jti)
- Истечение срока действия → JWTError
- Поддельный токен (неверная подпись) → JWTError
- Некорректный issuer → JWTError
"""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt, JWTError

from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestCreateAccessToken:
    """Тесты для CreateAccessToken."""

    def test_access_token_decodes_correctly(self):
        """Проверяет декодирование токена."""
        token = create_access_token(user_id=42, role="admin")
        payload = decode_token(token)

        assert payload.sub == "42"
        assert payload.role == "admin"
        assert payload.type == "access"
        assert payload.iss == "booking-auth-service"
        assert payload.jti is None  # у access-токена нет jti

    def test_access_token_has_correct_expiry(self):
        """Проверяет рабочий сценарий."""
        token = create_access_token(user_id=1, role="user")
        payload = decode_token(token)

        now = datetime.now(timezone.utc)
        assert payload.exp > now
        assert payload.exp < now + timedelta(minutes=16)  # 15 мин + запас


class TestCreateRefreshToken:
    """Тесты для CreateRefreshToken."""

    def test_refresh_token_decodes_correctly(self):
        """Проверяет декодирование токена."""
        token_str, jti, expires_at = create_refresh_token(
            user_id=7, role="user")
        payload = decode_token(token_str)

        assert payload.sub == "7"
        assert payload.role == "user"
        assert payload.type == "refresh"
        assert payload.jti == jti
        assert payload.iss == "booking-auth-service"

    def test_refresh_token_jti_is_unique(self):
        """Проверяет рабочий сценарий."""
        token1, jti1, _ = create_refresh_token(user_id=1, role="user")
        token2, jti2, _ = create_refresh_token(user_id=1, role="user")

        assert jti1 != jti2
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)
        assert payload1.jti == jti1
        assert payload2.jti == jti2

    def test_refresh_token_has_long_expiry(self):
        """Проверяет рабочий сценарий."""
        _, _, expires_at = create_refresh_token(user_id=1, role="user")

        now = datetime.now(timezone.utc)
        assert expires_at > now + timedelta(days=29)
        assert expires_at < now + timedelta(days=31)


class TestDecodeToken:
    """Тесты для DecodeToken."""

    def test_expired_token_raises_jwt_error(self, rsa_keys):
        """Проверяет сценарий с ошибкой."""
        private_pem, _ = rsa_keys
        expired_payload = {
            "sub": "1",
            "role": "user",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=10),
            "iat": datetime.now(timezone.utc) - timedelta(hours=1),
            "iss": "booking-auth-service",
        }
        expired_token = jwt.encode(
            expired_payload, private_pem, algorithm="RS256")

        with pytest.raises(JWTError):
            decode_token(expired_token)

    def test_wrong_issuer_raises_jwt_error(self, rsa_keys):
        """Проверяет сценарий с ошибкой."""
        private_pem, _ = rsa_keys
        bad_payload = {
            "sub": "1",
            "role": "user",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
            "iss": "wrong-issuer",
        }
        bad_token = jwt.encode(bad_payload, private_pem, algorithm="RS256")

        with pytest.raises(JWTError):
            decode_token(bad_token)

    def test_tampered_token_raises_jwt_error(self, rsa_keys):
        """Проверяет сценарий с ошибкой."""
        # Генерируем другую пару ключей — подпись не совпадёт
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        other_private = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)
        other_pem = other_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        payload = {
            "sub": "1",
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
            "iss": "booking-auth-service",
        }
        tampered_token = jwt.encode(payload, other_pem, algorithm="RS256")

        with pytest.raises(JWTError):
            decode_token(tampered_token)

    def test_malformed_token_raises_jwt_error(self):
        """Проверяет сценарий с ошибкой."""
        with pytest.raises(JWTError):
            decode_token("not.a.jwt")


class TestPasswordHashing:
    """Тесты для PasswordHashing."""

    def test_hash_password_returns_string(self):
        """Проверяет ожидаемый результат."""
        hashed = hash_password("MyStr0ngP@ss!")
        assert isinstance(hashed, str)
        assert "$argon2" in hashed

    def test_verify_password_correct(self):
        """Проверяет проверку пароля."""
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_password_incorrect(self):
        """Проверяет проверку пароля."""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_different_each_time(self):
        """Проверяет рабочий сценарий."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_both_verify_same(self):
        """Проверяет проверку пароля."""
        password = "same_password"
        h1 = hash_password(password)
        h2 = hash_password(password)
        assert verify_password(password, h1) is True
        assert verify_password(password, h2) is True
