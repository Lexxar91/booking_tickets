from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    """Схема для регистрации. Принимаем пароль открытым текстом — схема его не хранит."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Минимум 8 символов")


class UserRead(BaseModel):
    """Схема ответа — никогда не возвращаем hashed_password клиенту."""
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
    """Пара токенов которую возвращаем после успешного логина."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Payload внутри JWT токена.
    """
    sub: str          
    role: str
    type: str         
    exp: datetime
    iss: str
    jti: str | None = None


class RefreshTokenRequest(BaseModel):
    """Запрос на обновление токенов."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Запрос на отзыв refresh токена."""
    refresh_token: str
 
