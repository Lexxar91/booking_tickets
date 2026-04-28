"""
Общие фикстуры для тестов notification_service.

Цели:
- не зависеть от реального SMTP сервера
- изолировать побочные эффекты воркера
- тестировать оркестрацию без RabbitMQ и внешней сети
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def retry_task():
    """Выполняет retry task."""
    return SimpleNamespace(retry=MagicMock())
