"""
Unit-тесты для SMTP-отправки notification_service.
"""

from email import message_from_string
from email.header import decode_header, make_header

from src.services.smtp import send_email


class TestSendEmail:
    """Тесты отправки email."""
    def test_send_email_sends_html_message(self, monkeypatch):
        """Проверяет рабочий сценарий."""
        instances = []

        class FakeSMTP:
            """Фейковый SMTP-клиент для тестов."""
            def __init__(self, host, port):
                """Сохраняет параметры тестового клиента."""
                self.host = host
                self.port = port
                self.started_tls = False
                self.logged_in = None
                self.sent = None
                instances.append(self)

            def __enter__(self):
                """Открывает тестовый контекст."""
                return self

            def __exit__(self, exc_type, exc, tb):
                """Закрывает тестовый контекст."""
                return None

            def starttls(self):
                """Выполняет starttls."""
                self.started_tls = True

            def login(self, user, password):
                """Выполняет login."""
                self.logged_in = (user, password)

            def sendmail(self, from_addr, to_addr, message):
                """Выполняет sendmail."""
                self.sent = (from_addr, to_addr, message)

        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "2525")
        monkeypatch.setenv("SMTP_USER", "mailer@example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "top-secret")
        monkeypatch.setattr("src.services.smtp.smtplib.SMTP", FakeSMTP)

        send_email(
            to="user@example.com",
            subject="Ваш билет",
            html="<h1>Hello</h1>",
        )

        smtp = instances[0]
        assert smtp.host == "smtp.example.com"
        assert smtp.port == 2525
        assert smtp.started_tls is True
        assert smtp.logged_in == ("mailer@example.com", "top-secret")
        assert smtp.sent[0] == "mailer@example.com"
        assert smtp.sent[1] == "user@example.com"
        parsed = message_from_string(smtp.sent[2])
        assert str(make_header(decode_header(
            parsed["Subject"]))) == "Ваш билет"
        assert parsed["From"] == "mailer@example.com"
        assert parsed["To"] == "user@example.com"
        assert "<h1>Hello</h1>" in smtp.sent[2]

    def test_send_email_attaches_pdf_when_attachment_provided(
            self, monkeypatch):
        """Проверяет рабочий сценарий."""
        instances = []

        class FakeSMTP:
            """Фейковый SMTP-клиент для тестов."""
            def __init__(self, host, port):
                """Сохраняет параметры тестового клиента."""
                self.sent = None
                instances.append(self)

            def __enter__(self):
                """Открывает тестовый контекст."""
                return self

            def __exit__(self, exc_type, exc, tb):
                """Закрывает тестовый контекст."""
                return None

            def starttls(self):
                """Выполняет starttls."""
                return None

            def login(self, user, password):
                """Выполняет login."""
                return None

            def sendmail(self, from_addr, to_addr, message):
                """Выполняет sendmail."""
                self.sent = message

        monkeypatch.setenv("SMTP_USER", "mailer@example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "top-secret")
        monkeypatch.setattr("src.services.smtp.smtplib.SMTP", FakeSMTP)

        send_email(
            to="user@example.com",
            subject="Ticket",
            html="<p>Attached</p>",
            attachment=b"%PDF-1.4 fake",
            attachment_name="ticket_7.pdf",
        )

        message = instances[0].sent
        assert "ticket_7.pdf" in message
        assert "application/pdf" in message
