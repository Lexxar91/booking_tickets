import smtplib

from src.metrics import (
    track_email_retry,
    track_email_sent,
    track_pdf_generated,
)
from src.services.pdf import generate_ticket_pdf
from src.services.smtp import send_email
from src.services.templates import build_booking_confirmation_html
from src.worker import celery_app


@celery_app.task(
    name="send_booking_confirmation",
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    bind=True,
)
def send_booking_confirmation(
    self,
    booking_id: int,
    user_email: str,
    event_title: str,
    price: str,
) -> None:
    """Отправляет подтверждение бронирования."""
    try:
        pdf_bytes = generate_ticket_pdf(
            booking_id=booking_id,
            event_title=event_title,
            price=price,
            user_email=user_email,
        )
        track_pdf_generated(status="success")

        html = build_booking_confirmation_html(
            booking_id=booking_id,
            event_title=event_title,
            price=price,
        )

        send_email(
            to=user_email,
            subject=f"Ваш билет на {event_title} — бронирование #{booking_id}",
            html=html,
            attachment=pdf_bytes,
            attachment_name=f"ticket_{booking_id}.pdf",
        )

        track_email_sent(status="success")

        print(
            "✅ Email с PDF билетом отправлен на "
            f"{user_email} для бронирования #{booking_id}"
        )

    except smtplib.SMTPException as e:
        track_email_sent(status="failed")
        track_email_retry()
        print(f"❌ Ошибка SMTP: {e}. Повтор через 30 сек...")
        raise self.retry(exc=e)

    except Exception as e:
        track_email_sent(status="failed")
        print(f"❌ Неожиданная ошибка: {e}")
        raise
