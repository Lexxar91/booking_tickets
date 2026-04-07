"""Определения и helper-функции бизнес-метрик для auth_service."""

from prometheus_client import Counter, Gauge

STATUS_LABEL = ("status",)

auth_login_attempts_total = Counter(
    "auth_login_attempts_total",
    "Total number of login attempts",
    STATUS_LABEL,
)

auth_registrations_total = Counter(
    "auth_registrations_total",
    "Total number of registration attempts",
    STATUS_LABEL,
)

auth_token_refreshes_total = Counter(
    "auth_token_refreshes_total",
    "Total number of token refresh attempts",
    STATUS_LABEL,
)

auth_logouts_total = Counter(
    "auth_logouts_total",
    "Total number of logout attempts",
    STATUS_LABEL,
)

auth_active_sessions = Gauge(
    "auth_active_sessions",
    "Number of currently active user sessions",
)


def track_login_attempt(status: str) -> None:
    """Увеличивает счётчик попыток логина с нужным статусом."""
    auth_login_attempts_total.labels(status=status).inc()


def track_registration(status: str) -> None:
    """Увеличивает счётчик регистраций с нужным статусом."""
    auth_registrations_total.labels(status=status).inc()


def track_token_refresh(status: str) -> None:
    """Увеличивает счётчик refresh-операций с нужным статусом."""
    auth_token_refreshes_total.labels(status=status).inc()


def track_logout(status: str) -> None:
    """Увеличивает счётчик logout-операций с нужным статусом."""
    auth_logouts_total.labels(status=status).inc()


def increment_active_sessions() -> None:
    """Увеличивает gauge активных сессий после успешного логина."""
    auth_active_sessions.inc()


def decrement_active_sessions() -> None:
    """Уменьшает gauge активных сессий после успешного logout."""
    auth_active_sessions.dec()
