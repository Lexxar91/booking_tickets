"""
Unit-тесты для EventServices.

Тестируем только бизнес-логику сервисного слоя,
репозиторий подменяем mock-объектом.
"""

from unittest.mock import create_autospec

import pytest
from fastapi import HTTPException

from src.repositories.event_repo import EventRepository
from src.services.event_service import EventServices


def _build_service(repository: EventRepository |
                   None = None) -> tuple[EventServices, EventRepository]:
    """Собирает сервис и зависимости для теста."""
    repository = repository or create_autospec(EventRepository, instance=True)
    service = EventServices(repository)
    return service, repository


class TestEventServicesCreate:
    """Тесты создания мероприятий."""
    async def test_create_event_returns_repository_result(
            self, event_create_data, make_event):
        """Проверяет ожидаемый результат."""
        service, repository = _build_service()
        event = make_event(
            event_id=10,
            title=event_create_data.title,
            price=event_create_data.price)
        repository.create.return_value = event

        result = await service.create_event(event_create_data)

        assert result is event
        repository.create.assert_awaited_once_with(event_create_data)


class TestEventServicesGetEvent:
    """Тесты получения мероприятия."""
    async def test_get_event_returns_event_when_found(self, make_event):
        """Проверяет ожидаемый результат."""
        service, repository = _build_service()
        event = make_event(event_id=5)
        repository.get_by_event_id.return_value = event

        result = await service.get_event(5)

        assert result is event
        repository.get_by_event_id.assert_awaited_once_with(5)

    async def test_get_event_raises_404_when_not_found(self):
        """Проверяет ошибку 404."""
        service, repository = _build_service()
        repository.get_by_event_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.get_event(404)

        assert exc_info.value.status_code == 404


class TestEventServicesListEvents:
    """Тесты списка мероприятий."""
    async def test_list_events_returns_repository_result(self, make_event):
        """Проверяет ожидаемый результат."""
        service, repository = _build_service()
        events = [make_event(event_id=1), make_event(event_id=2)]
        repository.get_all_events.return_value = events

        result = await service.list_events(limit=10, offset=0)

        assert result == events
        repository.get_all_events.assert_awaited_once_with(limit=10, offset=0)


class TestEventServicesUpdate:
    """Тесты обновления мероприятия."""
    async def test_event_update_updates_existing_event(
            self, make_event, event_update_data):
        """Проверяет обновление данных."""
        service, repository = _build_service()
        event = make_event(event_id=7)
        updated_event = make_event(
            event_id=7, title="Updated concert", price=event_update_data.price)
        repository.get_by_event_id.return_value = event
        repository.event_update.return_value = updated_event

        result = await service.event_update(7, event_update_data)

        assert result is updated_event
        repository.get_by_event_id.assert_awaited_once_with(7)
        repository.event_update.assert_awaited_once_with(
            event, event_update_data)

    async def test_event_update_raises_404_for_missing_event(
            self, event_update_data):
        """Проверяет ошибку 404."""
        service, repository = _build_service()
        repository.get_by_event_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.event_update(999, event_update_data)

        assert exc_info.value.status_code == 404
        repository.event_update.assert_not_called()


class TestEventServicesDelete:
    """Тесты удаления мероприятия."""
    async def test_delete_event_deletes_existing_event(self, make_event):
        """Проверяет удаление данных."""
        service, repository = _build_service()
        event = make_event(event_id=12)
        repository.get_by_event_id.return_value = event

        result = await service.delete_event(12)

        assert result is None
        repository.get_by_event_id.assert_awaited_once_with(12)
        repository.event_delete.assert_awaited_once_with(event)

    async def test_delete_event_raises_404_for_missing_event(self):
        """Проверяет ошибку 404."""
        service, repository = _build_service()
        repository.get_by_event_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_event(999)

        assert exc_info.value.status_code == 404
        repository.event_delete.assert_not_called()
