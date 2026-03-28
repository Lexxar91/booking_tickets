from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.booking import Booking, BookingStatus, EventTickets
from src.schemas.booking import BookingCreate
from src.repositories.booking_repo import BookingRepository
from src.core.http_client import get_event


class BookingService:
    def __init__(self, repository: BookingRepository, session: AsyncSession):
        self.repository = repository
        self.session = session

    async def create(
        self,
        booking_data: BookingCreate,
        user_id: int,
    ) -> Booking:
        """
        Создание бронирования с защитой от Race Condition.

        Весь метод выполняется в одной транзакции:
        1. Получаем данные мероприятия из Event Service
        2. SELECT FOR UPDATE — блокируем строку мероприятия
        3. Проверяем наличие билетов
        4. Создаём бронирование
        5. Уменьшаем счётчик билетов в Event Service

        SELECT FOR UPDATE — это строчная блокировка (row-level lock).
        Пока транзакция А держит блокировку, транзакция Б будет ЖДАТЬ
        на этой же строке. Когда А сделает commit — Б увидит уже
        обновлённое значение available_tickets и либо купит последний
        билет, либо получит отказ. Двойная продажа невозможна.
        """

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
                available_tickets=event.get("total_tickets", None),
            )
            self.session.add(event_tickets)
            await self.session.flush()
        
        if event_tickets.available_tickets <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Билеты на это мероприятие закончились"
            )

        event_tickets.available_tickets -= 1
        await self.session.flush()

        return await self.repository.create_booking(
            user_id=user_id,
            event_id=booking_data.event_id,
            price_at_booking=Decimal(str(event["price"])),
        )
    
    async def get_booking(self, booking_id: int, user_id: int) -> Booking:
        """
        Получение бронирования.
        Проверяем что бронирование принадлежит текущему пользователю.
        """
        booking = await self.repository.get_by_booking_id(booking_id)
        
        if booking is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Бронирование с id={booking_id} не найдено"
            )
        
        if booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому бронированию"
            )
        return booking
        
    async def get_my_bookings(self, user_id: int) -> list[Booking]:
        """Получение всех бронирований текущего пользователя."""
        return await self.repository.get_by_user_id(user_id)
    

    async def cancel_booking(self, booking_id: int, user_id: int) -> Booking:
        """
        Отмена бронирования.
        Возвращаем билет — увеличиваем счётчик обратно.
        Тоже используем SELECT FOR UPDATE чтобы не было гонки.
        """

        booking = await self.get_booking(booking_id=booking_id, user_id=user_id)

        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Бронирование уже отменено"
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

        booking.status = BookingStatus.CANCELLED
        await self.session.flush()
        return booking