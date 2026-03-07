import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Text, Numeric, DateTime, func, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Event(Base):
    """
    Модель SQLAlchemy для таблицы мероприятий.
    
    Используем новый стиль SQLAlchemy 2.0 (Mapped Column).
    """
    __table_args__ = (
        CheckConstraint("date_end >= date_start", name="check_dates_valid"),
        {"schema": "events"},
    )
   
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        doc="Уникальный идентификатор мероприятия"
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Название мероприятия"
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Полное описание мероприятия"
    )

    # Работа с деньгами. Используем Numeric(precision, scale).
    # 10 знаков всего, 2 из них - копейки. (например: 12345678.99)
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Цена билета (базовая)"
    )

    total_tickets: Mapped[int] = mapped_column(
        Integer, 
        nullable=False,
        default=0,
        doc="Общее количество билетов в продаже"
    )

    date_start: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), # Важно: хранить дату с часовым поясом (Aware)
        nullable=False,
        doc="Дата и время начала мероприятия"
    )

    date_end: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        doc="Дата и время окончания (необязательно)"
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Время создания записи"
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        doc="Время последнего изменения записи"
    )

    def __repr__(self):
        """String representation для отладки"""
        return f"<Event(id={self.id}, title='{self.title}', price={self.price})>"
