from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LoginAttempt(Base):
    """Описывает модель попытки входа."""
    __tablename__ = "login_attempts"
    __table_args__ = {"schema": "auth"}

    bucket: Mapped[str] = mapped_column(String(320), primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
