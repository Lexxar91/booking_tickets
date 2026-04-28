"""Определения и helper-функции бизнес-метрик для event_service."""

from prometheus_client import Counter, Gauge

events_created_total = Counter(
    "events_created_total",
    "Total number of events created",
)

events_updated_total = Counter(
    "events_updated_total",
    "Total number of events updated",
)

events_deleted_total = Counter(
    "events_deleted_total",
    "Total number of events deleted",
)

# ---------------------------------------------------------------------------
# Gauges
# ---------------------------------------------------------------------------

total_events = Gauge(
    "total_events",
    "Current number of events in the system",
)


def track_event_created() -> None:
    """Выполняет track event created."""
    events_created_total.inc()


def track_event_updated() -> None:
    """Выполняет track event updated."""
    events_updated_total.inc()


def track_event_deleted() -> None:
    """Выполняет track event deleted."""
    events_deleted_total.inc()


def increment_total_events() -> None:
    """Выполняет increment total events."""
    total_events.inc()


def decrement_total_events() -> None:
    """Выполняет decrement total events."""
    total_events.dec()
