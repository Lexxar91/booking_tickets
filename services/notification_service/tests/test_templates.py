"""
Unit-тесты для HTML шаблонов notification_service.
"""

from src.services.templates import build_booking_confirmation_html


class TestBuildBookingConfirmationHtml:
    """Тесты HTML-шаблона бронирования."""
    def test_template_contains_booking_details(self):
        """Проверяет содержимое результата."""
        html = build_booking_confirmation_html(
            booking_id=17,
            event_title="Rock Festival",
            price="1999.00",
        )

        assert "Rock Festival" in html
        assert "#17" in html
        assert "1999.00" in html
        assert "BookingTickets" in html
