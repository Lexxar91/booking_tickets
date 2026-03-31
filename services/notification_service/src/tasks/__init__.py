# Импортируем все задачи, чтобы autodiscover_tasks их нашёл
from src.tasks.email import send_booking_confirmation  # noqa: F401

__all__ = ["send_booking_confirmation"]
