"""Проверяет гонки на отдельной БД с примененными миграциями.

Для запуска задайте BOOKING_TEST_DATABASE_URL (postgresql+asyncpg).
"""

import asyncio
import os
from collections.abc import AsyncIterator
from decimal import Decimal
from secrets import randbelow
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.models.booking import Booking, BookingStatus, EventTickets
from src.repositories.booking_repo import BookingRepository
from src.schemas.booking import BookingCreate
from src.services.booking_service import BookingService


@pytest.fixture
async def booking_database() -> AsyncIterator[tuple[async_sessionmaker, int]]:
    """Выдает сессии тестовой БД и удаляет созданные тестом записи."""
    url = os.environ.get("BOOKING_TEST_DATABASE_URL")
    if not url:
        pytest.skip("BOOKING_TEST_DATABASE_URL is not set")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    event_id = randbelow(2_000_000_000) + 1
    try:
        yield sessions, event_id
    finally:
        async with sessions() as session:
            await session.execute(
                delete(Booking).where(Booking.event_id == event_id))
            await session.execute(
                delete(EventTickets).where(EventTickets.event_id == event_id))
            await session.commit()
        await engine.dispose()


@pytest.mark.parametrize("total_tickets", [1, 2])
async def test_concurrent_first_purchases(
    booking_database: tuple[async_sessionmaker, int],
    monkeypatch: pytest.MonkeyPatch,
    total_tickets: int,
) -> None:
    """Две первые покупки не конфликтуют и не превышают остаток."""
    sessions, event_id = booking_database
    barrier = asyncio.Barrier(2)

    async def get_event(event_id: int) -> dict[str, object]:
        """Синхронизирует начало двух первых покупок."""
        await barrier.wait()
        return {"title": "Concert", "price": "10.00",
                "total_tickets": total_tickets}

    monkeypatch.setattr("src.services.booking_service.get_event", get_event)
    send_task = MagicMock()
    monkeypatch.setattr(
        "src.services.booking_service.celery_client.send_task", send_task)

    async def purchase() -> Booking | HTTPException:
        """Покупает билет в собственной транзакции."""
        async with sessions() as session:
            service = BookingService(BookingRepository(session), session)
            try:
                return await service.create(
                    BookingCreate(event_id=event_id, user_email="a@test.com"),
                    user_id=1,
                )
            except HTTPException as exc:
                await session.rollback()
                return exc

    results = await asyncio.wait_for(
        asyncio.gather(purchase(), purchase()), timeout=10)
    assert sum(isinstance(r, Booking) for r in results) == total_tickets
    assert all(r.status_code == 409 for r in results
               if isinstance(r, HTTPException))
    assert send_task.call_count == total_tickets
    async with sessions() as session:
        counter = await session.get(EventTickets, event_id)
        assert counter.available_tickets == 0
        count = await session.scalar(select(func.count()).select_from(
            Booking).where(Booking.event_id == event_id))
        assert count == total_tickets


async def test_concurrent_cancellations(
    booking_database: tuple[async_sessionmaker, int],
) -> None:
    """Две отмены прочитанной подтвержденной брони возвращают один билет."""
    sessions, event_id = booking_database
    async with sessions() as session:
        booking = Booking(user_id=1, event_id=event_id,
                          price_at_booking=Decimal("10.00"),
                          status=BookingStatus.CONFIRMED)
        session.add_all([booking, EventTickets(
            event_id=event_id, available_tickets=0)])
        await session.commit()
        booking_id = booking.id

    barrier = asyncio.Barrier(2)

    class ConcurrentRepository(BookingRepository):
        """Дожидается чтения исходного статуса обоими запросами."""

        async def get_by_booking_id(self, booking_id: int) -> Booking | None:
            """Возвращает бронь после одновременного чтения статуса."""
            result = await super().get_by_booking_id(booking_id)
            await barrier.wait()
            return result

    async def cancel() -> Booking | HTTPException:
        """Отменяет бронь в собственной транзакции."""
        async with sessions() as session:
            service = BookingService(ConcurrentRepository(session), session)
            try:
                result = await service.cancel_booking(booking_id, user_id=1)
                await session.commit()
                return result
            except HTTPException as exc:
                await session.rollback()
                return exc

    results = await asyncio.wait_for(
        asyncio.gather(cancel(), cancel()), timeout=10)
    assert sum(isinstance(r, Booking) for r in results) == 1
    errors = [r for r in results if isinstance(r, HTTPException)]
    assert len(errors) == 1 and errors[0].status_code == 409
    async with sessions() as session:
        counter = await session.get(EventTickets, event_id)
        booking = await session.get(Booking, booking_id)
        assert counter.available_tickets == 1
        assert booking.status == BookingStatus.CANCELLED
