"""Определения и helper-функции бизнес-метрик для booking_service."""

from prometheus_client import Counter, Gauge

STATUS_LABEL = ("status",)
EVENT_ID_LABEL = ("event_id",)

bookings_created_total = Counter(
    "bookings_created_total",
    "Total number of booking creation attempts",
    STATUS_LABEL,
)

bookings_cancelled_total = Counter(
    "bookings_cancelled_total",
    "Total number of booking cancellation attempts",
    STATUS_LABEL,
)

bookings_retrieved_total = Counter(
    "bookings_retrieved_total",
    "Total number of booking retrieval requests",
)

tickets_sold_per_event = Gauge(
    "tickets_sold_per_event",
    "Number of tickets sold per event",
    EVENT_ID_LABEL,
)

tickets_available_per_event = Gauge(
    "tickets_available_per_event",
    "Number of available tickets per event",
    EVENT_ID_LABEL,
)


def track_booking_created(status: str) -> None:
    """Увеличивает счётчик созданных бронирований с нужным статусом."""
    bookings_created_total.labels(status=status).inc()


def track_booking_cancelled(status: str) -> None:
    """Увеличивает счётчик отмен бронирований с нужным статусом."""
    bookings_cancelled_total.labels(status=status).inc()


def track_booking_retrieved() -> None:
    """Увеличивает счётчик запросов на чтение бронирований."""
    bookings_retrieved_total.inc()


def increment_tickets_sold(event_id: int) -> None:
    """Увеличивает счётчик проданных билетов для мероприятия."""
    tickets_sold_per_event.labels(event_id=str(event_id)).inc()


def set_tickets_available(event_id: int, available_tickets: int) -> None:
    """Обновляет gauge доступных билетов для мероприятия."""
    tickets_available_per_event.labels(event_id=str(event_id)).set(available_tickets)
