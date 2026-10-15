"""Публичный контракт браузерной сессии без JWT."""

from pydantic import BaseModel
from src.schemas.user import UserRead


class BrowserSessionRead(BaseModel):
    """Передает frontend пользователя и токен защиты от CSRF."""

    user: UserRead
    csrf_token: str
