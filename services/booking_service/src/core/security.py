from jose import jwt

from src.core.config import settings
from src.schemas.booking import TokenPayload


def decode_token(token: str) -> TokenPayload:
    """
    Декодируем и валидируем JWT токен.

    Booking Service только ПРОВЕРЯЕТ токены — не создаёт.
    Проверка происходит локально используя тот же SECRET_KEY что и Auth Service.
    Никакого запроса к Auth Service не нужно — это главное преимущество JWT.

    jose автоматически проверяет:
    - подпись (токен не был подделан)
    - срок жизни (exp — токен не протух)

    Raises:
        JWTError: если токен невалидный или протухший.
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    return TokenPayload(**payload)