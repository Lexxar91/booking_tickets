from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.models.booking import BookingStatus


class BookingCreate(BaseModel):
    """Описывает класс BookingCreate."""
    event_id: int = Field(..., gt=0)
    user_email: str = Field(..., description="Email для отправки билета")


class BookingRead(BaseModel):
    """Описывает класс BookingRead."""
    id: int
    user_id: int
    event_id: int
    status: BookingStatus
    price_at_booking: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('status', return_type=str)
    def serialize_status(self, value: BookingStatus) -> str:
        """Преобразует статус в строку."""
        return value.value


class TokenPayload(BaseModel):
    """Описывает payload JWT-токена."""
    sub: str
    role: str
    type: str
    exp: datetime
    iss: str
    jti: str | None = None
