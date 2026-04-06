"""
Unit-тесты для BookingService.

Подход:
- тестируем бизнес-логику сервисного слоя
- мокируем внешние зависимости: Event Service, Celery, repository, session
- не привязываемся к реальной БД или сети
"""

from decimal import Decimal
from unittest.mock import ANY, MagicMock, create_autospec

import pytest
from fastapi import HTTPException

from src.models.booking import BookingStatus
from src.repositories.booking_repo import BookingRepository
from src.schemas.booking import BookingCreate
from src.services.booking_service import BookingService


def _fake_scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _build_booking_service(
    repository: BookingRepository | None = None,
    session=None,
) -> tuple[BookingService, BookingRepository, object]:
    repository = repository or create_autospec(BookingRepository, instance=True)
    session = session or MagicMock()
    service = BookingService(repository=repository, session=session)
    return service, repository, session


class TestBookingServiceCreate:
    async def test_create_booking_with_existing_ticket_counter(
        self,
        monkeypatch,
        mock_session,
        make_booking,
        make_event_tickets,
    ):
        service, repository, _ = _build_booking_service(session=mock_session)
        booking_data = BookingCreate(event_id=11, user_email="user@example.com")
        event = {"id": 11, "title": "Concert", "price": "1500.00", "total_tickets": 5}
        event_tickets = make_event_tickets(event_id=11, available_tickets=3)
        booking = make_booking(booking_id=7, user_id=42, event_id=11, price_at_booking=Decimal("1500.00"))

        async def fake_get_event(event_id: int) -> dict:
            assert event_id == 11
            return event

        monkeypatch.setattr("src.services.booking_service.get_event", fake_get_event)
        send_task = MagicMock()
        monkeypatch.setattr("src.services.booking_service.celery_client.send_task", send_task)

        mock_session.execute.return_value = _fake_scalar_result(event_tickets)
        repository.create_booking.return_value = booking

        result = await service.create(booking_data=booking_data, user_id=42)

        assert result is booking
        assert event_tickets.available_tickets == 2
        repository.create_booking.assert_awaited_once_with(
            user_id=42,
            event_id=11,
            price_at_booking=Decimal("1500.00"),
        )
        send_task.assert_called_once_with(
            "send_booking_confirmation",
            kwargs={
                "booking_id": 7,
                "user_email": "user@example.com",
                "event_title": "Concert",
                "price": "1500.00",
            },
        )
        assert mock_session.add.call_count == 0
        assert mock_session.flush.await_count == 1

    async def test_create_booking_initializes_local_ticket_counter_on_first_booking(
        self,
        monkeypatch,
        mock_session,
        make_booking,
    ):
        service, repository, _ = _build_booking_service(session=mock_session)
        booking_data = BookingCreate(event_id=5, user_email="user@example.com")
        event = {"id": 5, "title": "First sale", "price": "999.99", "total_tickets": 2}
        booking = make_booking(booking_id=10, user_id=1, event_id=5, price_at_booking=Decimal("999.99"))

        async def fake_get_event(event_id: int) -> dict:
            return event

        monkeypatch.setattr("src.services.booking_service.get_event", fake_get_event)
        send_task = MagicMock()
        monkeypatch.setattr("src.services.booking_service.celery_client.send_task", send_task)

        mock_session.execute.return_value = _fake_scalar_result(None)
        repository.create_booking.return_value = booking

        result = await service.create(booking_data=booking_data, user_id=1)

        assert result is booking
        mock_session.add.assert_called_once()
        added_counter = mock_session.add.call_args.args[0]
        assert added_counter.event_id == 5
        assert added_counter.available_tickets == 1
        assert mock_session.flush.await_count == 2

    async def test_create_booking_raises_409_when_tickets_are_sold_out(
        self,
        monkeypatch,
        mock_session,
        make_event_tickets,
    ):
        service, repository, _ = _build_booking_service(session=mock_session)
        booking_data = BookingCreate(event_id=11, user_email="user@example.com")
        event_tickets = make_event_tickets(event_id=11, available_tickets=0)

        async def fake_get_event(event_id: int) -> dict:
            return {"id": 11, "title": "Concert", "price": "1500.00", "total_tickets": 5}

        monkeypatch.setattr("src.services.booking_service.get_event", fake_get_event)
        send_task = MagicMock()
        monkeypatch.setattr("src.services.booking_service.celery_client.send_task", send_task)

        mock_session.execute.return_value = _fake_scalar_result(event_tickets)

        with pytest.raises(HTTPException) as exc_info:
            await service.create(booking_data=booking_data, user_id=42)

        assert exc_info.value.status_code == 409
        repository.create_booking.assert_not_called()
        send_task.assert_not_called()


class TestBookingServiceGetBooking:
    async def test_get_booking_returns_booking_for_owner(self, mock_session, make_booking):
        service, repository, _ = _build_booking_service(session=mock_session)
        booking = make_booking(booking_id=1, user_id=7, event_id=22)
        repository.get_by_booking_id.return_value = booking

        result = await service.get_booking(booking_id=1, user_id=7)

        assert result is booking

    async def test_get_booking_raises_404_when_not_found(self, mock_session):
        service, repository, _ = _build_booking_service(session=mock_session)
        repository.get_by_booking_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.get_booking(booking_id=999, user_id=1)

        assert exc_info.value.status_code == 404

    async def test_get_booking_raises_403_for_foreign_booking(self, mock_session, make_booking):
        service, repository, _ = _build_booking_service(session=mock_session)
        repository.get_by_booking_id.return_value = make_booking(booking_id=1, user_id=100, event_id=22)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_booking(booking_id=1, user_id=7)

        assert exc_info.value.status_code == 403


class TestBookingServiceGetMyBookings:
    async def test_get_my_bookings_returns_repository_result(self, mock_session, make_booking):
        service, repository, _ = _build_booking_service(session=mock_session)
        bookings = [make_booking(booking_id=1, user_id=5), make_booking(booking_id=2, user_id=5)]
        repository.get_by_user_id.return_value = bookings

        result = await service.get_my_bookings(user_id=5)

        assert result == bookings
        repository.get_by_user_id.assert_awaited_once_with(user_id=5)


class TestBookingServiceCancelBooking:
    async def test_cancel_booking_marks_booking_as_cancelled_and_returns_ticket(
        self,
        mock_session,
        make_booking,
        make_event_tickets,
    ):
        service, repository, _ = _build_booking_service(session=mock_session)
        booking = make_booking(booking_id=3, user_id=1, event_id=9, status=BookingStatus.CONFIRMED)
        event_tickets = make_event_tickets(event_id=9, available_tickets=0)

        repository.get_by_booking_id.return_value = booking
        mock_session.execute.return_value = _fake_scalar_result(event_tickets)

        result = await service.cancel_booking(booking_id=3, user_id=1)

        assert result is booking
        assert booking.status == BookingStatus.CANCELLED
        assert event_tickets.available_tickets == 1
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(booking)

    async def test_cancel_booking_raises_409_when_already_cancelled(self, mock_session, make_booking):
        service, repository, _ = _build_booking_service(session=mock_session)
        repository.get_by_booking_id.return_value = make_booking(
            booking_id=3,
            user_id=1,
            event_id=9,
            status=BookingStatus.CANCELLED,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.cancel_booking(booking_id=3, user_id=1)

        assert exc_info.value.status_code == 409
        mock_session.execute.assert_not_called()

    async def test_cancel_booking_allows_missing_local_counter(
        self,
        mock_session,
        make_booking,
    ):
        service, repository, _ = _build_booking_service(session=mock_session)
        booking = make_booking(booking_id=3, user_id=1, event_id=9, status=BookingStatus.CONFIRMED)

        repository.get_by_booking_id.return_value = booking
        mock_session.execute.return_value = _fake_scalar_result(None)

        result = await service.cancel_booking(booking_id=3, user_id=1)

        assert result is booking
        assert booking.status == BookingStatus.CANCELLED
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(booking)
