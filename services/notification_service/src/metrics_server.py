"""
Отдельный HTTP-сервер для экспорта метрик Prometheus.

Notification_service — Celery worker без встроенного HTTP.
Этот модуль поднимает лёгкий WSGI-сервер на порту 9100,
чтобы Prometheus мог scrape'ить метрики.

Запускается как отдельный процесс в контейнере:
    python -m src.metrics_server
"""

import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

METRICS_PORT = int(os.getenv("METRICS_PORT", "9100"))


class MetricsHandler(BaseHTTPRequestHandler):
    """Простой HTTP handler для Prometheus scrape endpoint."""

    def do_GET(self) -> None:
        """Возвращает метрики по пути `/metrics`."""
        if self.path == "/metrics":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
            return

        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        """Отключаем логирование каждого запроса в production."""
        return None


def run_metrics_server(port: int = METRICS_PORT) -> None:
    """Запускает HTTP-сервер для экспорта метрик."""
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"Metrics server started on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    run_metrics_server()
