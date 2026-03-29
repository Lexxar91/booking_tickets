import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    price: str
):
    """
    Celery задача — отправка email подтверждения бронирования.

    bind=True нужен для доступа к self.retry() — механизму повторных попыток.
    Если email сервер недоступен — задача не потеряется, а встанет обратно
    в очередь и попробует снова через 30 секунд.
    """
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")


        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Подтверждение бронирования #{booking_id}"
        msg["From"] = smtp_user
        msg["To"] = user_email

        # HTML версия письма
        html = f"""
        <html>
        <body>
            <h2>Ваше бронирование подтверждено!</h2>
            <p>Мероприятие: <strong>{event_title}</strong></p>
            <p>Номер бронирования: <strong>#{booking_id}</strong></p>
            <p>Стоимость: <strong>{price} ₽</strong></p>
            <p>Спасибо за покупку!</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, user_email, msg.as_string())

        print(f"✅ Email отправлен на {user_email} для бронирования #{booking_id}")

    except smtplib.SMTPException as e:
        print(f"❌ Ошибка отправки email: {e}. Повтор через 30 сек...")
        raise self.retry(exc=e)
    
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        raise