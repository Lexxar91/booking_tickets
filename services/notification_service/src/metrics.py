"""Определения и helper-функции бизнес-метрик для notification_service."""

from prometheus_client import Counter

STATUS_LABEL = ("status",)

emails_sent_total = Counter(
    "emails_sent_total",
    "Total number of email sending attempts",
    STATUS_LABEL,
)

emails_retry_total = Counter(
    "emails_retry_total",
    "Total number of email retry attempts",
)

pdf_generated_total = Counter(
    "pdf_generated_total",
    "Total number of PDF generation attempts",
    STATUS_LABEL,
)


def track_email_sent(status: str) -> None:
    """Выполняет track email sent."""
    emails_sent_total.labels(status=status).inc()


def track_email_retry() -> None:
    """Выполняет track email retry."""
    emails_retry_total.inc()


def track_pdf_generated(status: str) -> None:
    """Выполняет track pdf generated."""
    pdf_generated_total.labels(status=status).inc()
