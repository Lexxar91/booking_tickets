from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class BookingStatus(PyEnum):
    """
    Статусы бронирования.
    
    PENDING    — бронирование создано, ожидает оплаты (в нашем случае сразу CONFIRMED)
    CONFIRMED  — оплачено и подтверждено
    CANCELLED  — отменено пользователем
    """
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Booking(Base):
    __table_args__ = {"schema": "booking"}

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    status: Mapped[BookingStatus] = mapped_column(
        SQLEnum(BookingStatus, schema="booking"),
        default=BookingStatus.CONFIRMED,
        nullable=False
    )

    price_at_booking: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Booking id={self.id} user_id={self.user_id} event_id={self.event_id} status={self.status}>"
