from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.models.booking import BookingStatus


class BookingCreate(BaseModel):
    """Схема для создания бронирования — клиент передаёт только event_id."""
    event_id: int = Field(..., gt=0)


class BookingRead(BaseModel):
    """Схема ответа клиенту."""
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
        return value.value



class TokenPayload(BaseModel):
    """
    Payload внутри JWT токена.
    """
    sub: str       
    role: str
    type: str      
    exp: datetime