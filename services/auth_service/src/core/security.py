from datetime import datetime, timedelta, timezone
from re import S
from warnings import deprecated
from fastapi.background import P
from passlib.context import CryptContext
from jose import JWTError, jwt
 
from src.core.config import settings
from src.schemas.user import TokenPayload


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Хэшируем пароль перед сохранением в БД."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяем пароль при логине.
    Никогда не сравниваем пароли напрямую — только через эту функцию.
    """
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(payload: dict, expires_delta: timedelta) -> str:
    """
    Внутренняя функция создания токена.
    """
    expire = datetime.now(timezone.utc) + expires_delta
    payload["exp"] = expire
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    """
    Access Token (15-30 минут).
    Используется клиентом в каждом запросе в заголовке:
    Authorization: Bearer <access_token>
    """
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
    }
    return _create_token(payload, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: int, role: str) -> str:
    """
    Refresh Token (30 дней).
    Используется только для получения нового access токена.
    Храним его хэш в БД — чтобы можно было отозвать при logout.
    """
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> TokenPayload:
    """
    Декодируем и валидируем токен.
    jose автоматически проверяет:
    - подпись (signature) — токен не был подделан
    - срок жизни (exp) — токен не протух
 
    Raises:
        JWTError: если токен невалидный или протухший.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return TokenPayload(**payload)
 
 