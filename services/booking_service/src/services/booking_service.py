from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.celery_client import celery_client
from src.core.metrics import (
    increment_tickets_sold,
    set_tickets_available,
    track_booking_cancelled,
    track_booking_created,
    track_booking_retrieved,
)
from src.core.http_client import get_event
from src.models.booking import Booking, BookingStatus, EventTickets
from src.repositories.booking_repo import BookingRepository
from src.schemas.booking import BookingCreate


class BookingService:
    """Содержит бизнес-логику бронирований."""
    def __init__(self, repository: BookingRepository, session: AsyncSession):
        """Сохраняет зависимости сервиса."""
        self.repository = repository
        self.session = session

    async def create(
        self,
        booking_data: BookingCreate,
        user_id: int,
    ) -> Booking:
        """Создает бронирование."""

        event = await get_event(booking_data.event_id)

        stmt = (
            select(EventTickets)
            .where(EventTickets.event_id == booking_data.event_id)
            .with_for_update()
        )

        result = await self.session.execute(stmt)
        event_tickets = result.scalar_one_or_none()

        if event_tickets is None:
            event_tickets = EventTickets(
                event_id=booking_data.event_id,
                available_tickets=event.get("total_tickets"),
            )
            self.session.add(event_tickets)
            await self.session.flush()

        if event_tickets.available_tickets <= 0:
            track_booking_created(status="failed")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Билеты на это мероприятие закончились",
            )

        event_tickets.available_tickets -= 1
        await self.session.flush()

        booking = await self.repository.create_booking(
            user_id=user_id,
            event_id=booking_data.event_id,
            price_at_booking=Decimal(str(event["price"])),
        )

        track_booking_created(status="success")
        increment_tickets_sold(event_id=booking_data.event_id)
        set_tickets_available(
            event_id=booking_data.event_id,
            available_tickets=event_tickets.available_tickets,
        )

        celery_client.send_task(
            "send_booking_confirmation",
            kwargs={
                "booking_id": booking.id,
                "user_email": booking_data.user_email,
                "event_title": event["title"],
                "price": str(booking.price_at_booking),
            },
        )

        return booking

    async def get_booking(self, booking_id: int, user_id: int) -> Booking:
        """Возвращает бронирование пользователя."""
        track_booking_retrieved()
        booking = await self.repository.get_by_booking_id(booking_id)

        if booking is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Бронирование с id={booking_id} не найдено",
            )

        if booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому бронированию",
            )
        return booking

    async def get_my_bookings(self, user_id: int) -> list[Booking]:
        """Возвращает список бронирований пользователя."""
        return await self.repository.get_by_user_id(user_id)

    async def cancel_booking(self, booking_id: int, user_id: int) -> Booking:
        """Отменяет бронирование пользователя."""

        booking = await self.get_booking(
            booking_id=booking_id,
            user_id=user_id,
        )

        if booking.status == BookingStatus.CANCELLED:
            track_booking_cancelled(status="not_found")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Бронирование уже отменено",
            )

        stmt = (
            select(EventTickets)
            .where(EventTickets.event_id == booking.event_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        event_tickets = result.scalar_one_or_none()

        if event_tickets:
            event_tickets.available_tickets += 1
            set_tickets_available(
                event_id=booking.event_id,
                available_tickets=event_tickets.available_tickets,
            )

        booking.status = BookingStatus.CANCELLED
        await self.session.flush()
        await self.session.refresh(booking)

        track_booking_cancelled(status="success")

        return booking
