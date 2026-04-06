"""
Unit-тесты для core/http_client.py.

Проверяем только трансляцию внешних HTTP-ошибок в доменные HTTPException.
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException

from src.core.http_client import get_event


class _FakeAsyncClient:
    def __init__(self, response=None, exc: Exception | None = None):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, *_args, **_kwargs):
        if self._exc is not None:
            raise self._exc
        return self._response


class TestGetEvent:
    async def test_get_event_returns_json_on_success(self, monkeypatch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"id": 1, "title": "Concert"}
        response.raise_for_status.return_value = None

        monkeypatch.setattr(
            "src.core.http_client.httpx.AsyncClient",
            lambda timeout=5: _FakeAsyncClient(response=response),
        )

        result = await get_event(1)

        assert result == {"id": 1, "title": "Concert"}

    async def test_get_event_raises_404_when_event_not_found(self, monkeypatch):
        response = MagicMock(status_code=404)

        monkeypatch.setattr(
            "src.core.http_client.httpx.AsyncClient",
            lambda timeout=5: _FakeAsyncClient(response=response),
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_event(99)

        assert exc_info.value.status_code == 404

    async def test_get_event_raises_503_on_timeout(self, monkeypatch):
        monkeypatch.setattr(
            "src.core.http_client.httpx.AsyncClient",
            lambda timeout=5: _FakeAsyncClient(exc=httpx.TimeoutException("timeout")),
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_event(1)

        assert exc_info.value.status_code == 503
        assert "timeout" in exc_info.value.detail.lower()

    async def test_get_event_raises_503_on_request_error(self, monkeypatch):
        request = httpx.Request("GET", "http://event_service:8000/api/v1/events/1")
        monkeypatch.setattr(
            "src.core.http_client.httpx.AsyncClient",
            lambda timeout=5: _FakeAsyncClient(exc=httpx.RequestError("boom", request=request)),
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_event(1)

        assert exc_info.value.status_code == 503
