"""Серверное хранилище браузерных сессий BFF."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class BrowserSession(Base):
    """Хранит хеш cookie, CSRF-токен и зашифрованные JWT."""

    __tablename__ = "browser_sessions"
    __table_args__ = {"schema": "auth"}

    id_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False,
    )
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    access_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
