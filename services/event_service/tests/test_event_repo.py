"""
Unit-тесты для EventRepository.

Проверяем:
- создание мероприятия
- получение одного и списка мероприятий
- частичное обновление и удаление
"""

from decimal import Decimal
from unittest.mock import MagicMock

from src.repositories.event_repo import EventRepository
from src.schemas.event import EventUpdate


def _fake_scalar_result(value):
    """Создает фейковый scalar-результат."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _fake_scalars_result(values):
    """Создает фейковый scalars-результат."""
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


class TestEventRepository:
    """Тесты репозитория мероприятий."""
    async def test_create_persists_event(
            self, mock_session, event_create_data):
        """Проверяет сохранение данных."""
        repo = EventRepository(mock_session)

        event = await repo.create(event_create_data)

        mock_session.add.assert_called_once_with(event)
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(event)
        assert event.title == event_create_data.title
        assert event.price == event_create_data.price

    async def test_get_by_event_id_returns_event(
            self, mock_session, make_event):
        """Проверяет ожидаемый результат."""
        event = make_event(event_id=4)
        mock_session.execute.return_value = _fake_scalar_result(event)
        repo = EventRepository(mock_session)

        result = await repo.get_by_event_id(4)

        assert result is event

    async def test_get_all_events_returns_sequence(
            self, mock_session, make_event):
        """Проверяет ожидаемый результат."""
        events = [make_event(event_id=1), make_event(event_id=2)]
        mock_session.execute.return_value = _fake_scalars_result(events)
        repo = EventRepository(mock_session)

        result = await repo.get_all_events(limit=10, offset=5)

        assert list(result) == events

    async def test_event_update_updates_only_provided_fields(
            self, mock_session, make_event):
        """Проверяет обновление данных."""
        event = make_event(event_id=9, title="Old title",
                           price=Decimal("1000.00"))
        update_data = EventUpdate(title="New title")
        repo = EventRepository(mock_session)

        result = await repo.event_update(event, update_data)

        assert result is event
        assert event.title == "New title"
        assert event.price == Decimal("1000.00")
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(event)

    async def test_event_delete_deletes_event_and_flushes(
            self, mock_session, make_event):
        """Проверяет удаление данных."""
        event = make_event(event_id=10)
        repo = EventRepository(mock_session)

        await repo.event_delete(event)

        mock_session.delete.assert_awaited_once_with(event)
        mock_session.flush.assert_awaited_once()
