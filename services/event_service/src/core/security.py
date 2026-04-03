from jose import jwt

from src.core.config import settings
from src.schemas.auth import TokenPayload


def decode_token(token: str) -> TokenPayload:
    payload = jwt.decode(
        token,
        settings.jwt_public_key,
        algorithms=[settings.ALGORITHM],
        issuer=settings.JWT_ISSUER,
    )
    return TokenPayload(**payload)
