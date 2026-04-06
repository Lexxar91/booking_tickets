"""
API-тесты для роутов booking_service.

Проверяем:
- wiring роутов и dependency overrides
- commit только там, где он действительно нужен
- передачу user id и payload в сервисный слой
"""

from unittest.mock import AsyncMock, create_autospec

from src.api.v1.bookings import booking_create, cancel_booking, get_booking, get_my_bookings
from src.models.booking import BookingStatus
from src.schemas.booking import BookingCreate
from src.services.booking_service import BookingService


class TestBookingsApi:
    async def test_create_booking_returns_created_booking_and_commits(self, make_booking):
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(BookingService, instance=True)
        service.create.return_value = make_booking(booking_id=7, user_id=42, event_id=11)

        result = await booking_create(
            booking_in=BookingCreate(event_id=11, user_email="user@example.com"),
            current_user_id=42,
            session=session,
            service=service,
        )

        assert result.id == 7
        session.commit.assert_awaited_once()
        assert service.create.await_args.kwargs["user_id"] == 42
        booking_data = service.create.await_args.kwargs["booking_data"]
        assert booking_data.event_id == 11
        assert booking_data.user_email == "user@example.com"

    async def test_get_my_bookings_returns_service_result_without_commit(self, make_booking):
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(BookingService, instance=True)
        service.get_my_bookings.return_value = [
            make_booking(booking_id=1, user_id=42),
            make_booking(booking_id=2, user_id=42),
        ]

        result = await get_my_bookings(
            service=service,
            current_user_id=42,
        )

        assert len(result) == 2
        service.get_my_bookings.assert_awaited_once_with(user_id=42)
        session.commit.assert_not_called()

    async def test_get_booking_returns_requested_booking(self, make_booking):
        session = AsyncMock()
        service = create_autospec(BookingService, instance=True)
        service.get_booking.return_value = make_booking(booking_id=5, user_id=42, event_id=9)

        result = await get_booking(
            booking_id=5,
            service=service,
            current_user_id=42,
        )

        assert result.event_id == 9
        service.get_booking.assert_awaited_once_with(booking_id=5, user_id=42)

    async def test_cancel_booking_returns_updated_booking_and_commits(self, make_booking):
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(BookingService, instance=True)
        service.cancel_booking.return_value = make_booking(
            booking_id=3,
            user_id=42,
            status=BookingStatus.CANCELLED,
        )

        result = await cancel_booking(
            booking_id=3,
            session=session,
            service=service,
            current_user_id=42,
        )

        assert result.status == BookingStatus.CANCELLED
        service.cancel_booking.assert_awaited_once_with(3, 42)
        session.commit.assert_awaited_once()
