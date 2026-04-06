"""
Unit-тесты для BookingRepository.

Проверяем:
- создание бронирования
- поиск по `booking_id`
- выборку бронирований пользователя
"""

from decimal import Decimal
from unittest.mock import MagicMock

from src.models.booking import BookingStatus
from src.repositories.booking_repo import BookingRepository


def _fake_scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _fake_scalars_result(values):
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


class TestBookingRepository:
    async def test_create_booking_persists_confirmed_booking(self, mock_session):
        repo = BookingRepository(mock_session)

        booking = await repo.create_booking(
            user_id=7,
            event_id=12,
            price_at_booking=Decimal("1500.00"),
        )

        mock_session.add.assert_called_once_with(booking)
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(booking)
        assert booking.user_id == 7
        assert booking.event_id == 12
        assert booking.status == BookingStatus.CONFIRMED

    async def test_get_by_booking_id_returns_booking(self, mock_session, make_booking):
        booking = make_booking(booking_id=8)
        mock_session.execute.return_value = _fake_scalar_result(booking)
        repo = BookingRepository(mock_session)

        result = await repo.get_by_booking_id(8)

        assert result is booking

    async def test_get_by_user_id_returns_all_user_bookings(self, mock_session, make_booking):
        bookings = [make_booking(booking_id=1, user_id=5), make_booking(booking_id=2, user_id=5)]
        mock_session.execute.return_value = _fake_scalars_result(bookings)
        repo = BookingRepository(mock_session)

        result = await repo.get_by_user_id(5)

        assert result == bookings
