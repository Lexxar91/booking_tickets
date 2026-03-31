import smtplib

from src.worker import celery_app
from src.services.pdf import generate_ticket_pdf
from src.services.smtp import send_email
from src.services.templates import build_booking_confirmation_html


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
    """
    Celery задача — оркестратор отправки билета.
    Единственная ответственность: координация вызовов сервисов.

    Намеренно не содержит деталей реализации PDF или SMTP —
    только вызывает нужные сервисы в правильном порядке.
    При ошибке SMTP — retry через 30 секунд (максимум 3 раза).
    """
    try:
        pdf_bytes = generate_ticket_pdf(
            booking_id=booking_id,
            event_title=event_title,
            price=price,
            user_email=user_email,
        )

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

        print(f"✅ Email с PDF билетом отправлен на {user_email} для бронирования #{booking_id}")

    except smtplib.SMTPException as e:
        print(f"❌ Ошибка SMTP: {e}. Повтор через 30 сек...")
        raise self.retry(exc=e)

    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        raise