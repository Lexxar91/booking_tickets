from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    """Описывает класс UserRegister."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Минимум 8 символов")


class UserRead(BaseModel):
    """Описывает класс UserRead."""
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# TOKEN SCHEMAS
# ==============================================================================


class TokenPair(BaseModel):
    """Описывает класс TokenPair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Описывает payload JWT-токена."""
    sub: str
    role: str
    type: str
    exp: datetime
    iss: str
    jti: str | None = None


class RefreshTokenRequest(BaseModel):
    """Описывает класс RefreshTokenRequest."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Описывает класс LogoutRequest."""
    refresh_token: str
