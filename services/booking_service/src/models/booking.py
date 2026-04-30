from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class BookingStatus(PyEnum):
    """Описывает класс BookingStatus."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Booking(Base):
    """Описывает модель бронирования."""
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

    @property
    def status_str(self) -> str:
        """Возвращает статус в виде строки."""
        return self.status.value

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта."""
        return (
            f"<Booking id={self.id} "
            f"user_id={self.user_id} "
            f"event_id={self.event_id} "
            f"status={self.status}>"
        )


class EventTickets(Base):
    """Описывает локальный счетчик билетов."""
    __tablename__ = "event_tickets"
    __table_args__ = {"schema": "booking"}

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    available_tickets: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта."""
        return (
            f"<EventTickets event_id={self.event_id} "
            f"available={self.available_tickets}>"
        )
