from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventBase(BaseModel):
    """Описывает класс EventBase."""
    title: str = Field(..., min_length=3, max_length=255,
                       description="Название мероприятия")
    description: str | None = Field(None, description="Описание мероприятия")
    price: Decimal = Field(..., gt=0, decimal_places=2,
                           description="Цена билета")
    total_tickets: int = Field(..., ge=1, description="Количество билетов")
    date_start: datetime = Field(..., description="Дата и время начала")
    date_end: datetime = Field(..., description="Дата и время окончания")

    @model_validator(mode='after')
    def check_dates(self) -> 'EventBase':
        """Проверяет корректность диапазона дат."""
        if self.date_end <= self.date_start:
            raise ValueError("date_end должно быть строго после date_start")
        return self


class EventCreate(EventBase):
    """Описывает класс EventCreate."""
    pass


class EventUpdate(BaseModel):
    """Описывает класс EventUpdate."""
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = Field(None)
    price: Decimal | None = Field(None, gt=0, decimal_places=2)
    total_tickets: int | None = Field(None, ge=1)
    date_start: datetime | None = Field(None)
    date_end: datetime | None = Field(None)

    @model_validator(mode='after')
    def check_dates(self) -> 'EventUpdate':
        """Проверяет корректность диапазона дат."""
        if self.date_start and self.date_end:
            if self.date_end <= self.date_start:
                raise ValueError(
                    "date_end должно быть строго после date_start")
        return self


class EventRead(EventBase):
    """Описывает класс EventRead."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
