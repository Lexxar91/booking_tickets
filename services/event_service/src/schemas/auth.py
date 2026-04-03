from datetime import datetime

from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    role: str
    type: str
    exp: datetime
    iss: str
    jti: str | None = None
