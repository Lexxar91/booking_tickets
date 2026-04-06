"""
Unit-тесты для Celery-задачи отправки письма.
"""

import smtplib

import pytest

from src.tasks.email import send_booking_confirmation


class RetryTriggered(Exception):
    """Техническое исключение для проверки retry-пути в тестах."""


class TestSendBookingConfirmationTask:
    def test_task_builds_pdf_html_and_sends_email(self, monkeypatch, retry_task):
        monkeypatch.setattr("src.tasks.email.generate_ticket_pdf", lambda **kwargs: b"%PDF-test")
        monkeypatch.setattr("src.tasks.email.build_booking_confirmation_html", lambda **kwargs: "<h1>ok</h1>")

        captured = {}

        def fake_send_email(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("src.tasks.email.send_email", fake_send_email)

        send_booking_confirmation.run(
            booking_id=17,
            user_email="user@example.com",
            event_title="Rock Festival",
            price="2500.00",
        )

        assert captured["to"] == "user@example.com"
        assert captured["attachment"] == b"%PDF-test"
        assert captured["attachment_name"] == "ticket_17.pdf"
        assert "Rock Festival" in captured["subject"]

    def test_task_retries_on_smtp_exception(self, monkeypatch):
        monkeypatch.setattr("src.tasks.email.generate_ticket_pdf", lambda **kwargs: b"%PDF-test")
        monkeypatch.setattr("src.tasks.email.build_booking_confirmation_html", lambda **kwargs: "<h1>ok</h1>")
        monkeypatch.setattr(
            "src.tasks.email.send_email",
            lambda **kwargs: (_ for _ in ()).throw(smtplib.SMTPException("smtp failed")),
        )
        monkeypatch.setattr(
            send_booking_confirmation,
            "retry",
            lambda *, exc: (_ for _ in ()).throw(RetryTriggered(exc)),
        )

        with pytest.raises(RetryTriggered):
            send_booking_confirmation.run(
                booking_id=18,
                user_email="user@example.com",
                event_title="Rock Festival",
                price="2500.00",
            )

    def test_task_reraises_unexpected_exception(self, monkeypatch, retry_task):
        monkeypatch.setattr(
            "src.tasks.email.generate_ticket_pdf",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("pdf failed")),
        )

        with pytest.raises(RuntimeError, match="pdf failed"):
            send_booking_confirmation.run(
                booking_id=19,
                user_email="user@example.com",
                event_title="Rock Festival",
                price="2500.00",
            )
