from datetime import datetime

from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Описывает payload JWT-токена."""
    sub: str
    role: str
    type: str
    exp: datetime
    iss: str
    jti: str | None = None
