from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from src.core.config import settings
from src.schemas.user import TokenPayload

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Выполняет hash password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Выполняет verify password."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(payload: dict, expires_delta: timedelta) -> str:
    """Создает JWT-токен с общими полями."""
    expire = datetime.now(timezone.utc) + expires_delta
    token_payload = {
        **payload,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": settings.JWT_ISSUER,
    }
    return jwt.encode(
        token_payload,
        settings.jwt_private_key,
        algorithm=settings.ALGORITHM,
    )


def create_access_token(user_id: int, role: str) -> str:
    """Создает access-токен."""
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
    }
    return _create_token(
        payload, timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: int, role: str) -> tuple[str, str, datetime]:
    """Создает refresh-токен."""
    jti = str(uuid4())
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
        "jti": jti,
    }
    return _create_token(payload, expires_delta), jti, expires_at


def decode_token(token: str) -> TokenPayload:
    """Декодирует JWT-токен."""
    payload = jwt.decode(
        token,
        settings.jwt_public_key,
        algorithms=[settings.ALGORITHM],
        issuer=settings.JWT_ISSUER,
    )
    return TokenPayload(**payload)


__all__ = [
    "JWTError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
