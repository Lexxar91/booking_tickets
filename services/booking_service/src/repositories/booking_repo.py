from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.booking import Booking, BookingStatus


class BookingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_booking(
            self,
            user_id: int,
            event_id: int,
            price_at_booking: Decimal,
    ) -> Booking:
        """Создаём запись бронирования."""
        booking = Booking(
            user_id=user_id,
            event_id=event_id,
            price_at_booking=price_at_booking,
            status=BookingStatus.CONFIRMED
        )
        self.session.add(booking)
        await self.session.flush()
        await self.session.refresh(booking)
        return booking
    
    async def get_by_booking_id(self, booking_id: int) -> Booking | None:
        stmt = select(Booking).where(Booking.id == booking_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, user_id: int) -> list[Booking]:
        """Все бронирования конкретного пользователя"""
        stmt = select(Booking).where(Booking.user_id == user_id)
        results = await self.session.execute(stmt)
        return list(results.scalars().all())
