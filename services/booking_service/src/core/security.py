from jose import jwt

from src.core.config import settings
from src.schemas.booking import TokenPayload


def decode_token(token: str) -> TokenPayload:
    """
    Декодируем и валидируем JWT токен.

    Booking Service только проверяет access токены.
    Для этого ему нужен только публичный ключ Auth Service,
    а приватный ключ остаётся внутри auth_service.

    jose автоматически проверяет подпись, срок жизни токена и issuer.

    Raises:
        JWTError: если токен невалидный или протухший.
    """
    payload = jwt.decode(
        token,
        settings.jwt_public_key,
        algorithms=[settings.ALGORITHM],
        issuer=settings.JWT_ISSUER,
    )
    return TokenPayload(**payload)
