"""
Unit-тесты для генерации PDF билета.
"""

from src.services.pdf import generate_ticket_pdf


class TestGenerateTicketPdf:
    """Тесты генерации PDF-билета."""
    def test_generate_ticket_pdf_returns_non_empty_pdf_bytes(self):
        """Проверяет ожидаемый результат."""
        pdf_bytes = generate_ticket_pdf(
            booking_id=7,
            event_title="Jazz Night",
            price="1499.00",
            user_email="user@example.com",
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 100
