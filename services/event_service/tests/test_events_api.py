"""
API-тесты для роутов event_service.

Проверяем:
- wiring роутов и dependency overrides
- commit на write-операциях
- передачу admin context и query params в сервисный слой
"""

from unittest.mock import AsyncMock, create_autospec

from src.api.v1.events import create_event, delete_event, event_update, get_event, list_events
from src.schemas.event import EventCreate, EventUpdate
from src.services.event_service import EventServices


class TestEventsApi:
    async def test_create_event_returns_created_event_and_commits(self, make_event):
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(EventServices, instance=True)
        service.create_event.return_value = make_event(event_id=5, title="Concert")

        result = await create_event(
            event_in=EventCreate(
                title="Concert",
                description="Big live show",
                price="1500.00",
                total_tickets=100,
                date_start="2026-04-20T18:00:00Z",
                date_end="2026-04-20T21:00:00Z",
            ),
            _=1,
            service=service,
            session=session,
        )

        assert result.id == 5
        session.commit.assert_awaited_once()
        event_in = service.create_event.await_args.args[0]
        assert event_in.title == "Concert"

    async def test_list_events_passes_pagination_to_service(self, make_event):
        session = AsyncMock()
        service = create_autospec(EventServices, instance=True)
        service.list_events.return_value = [make_event(event_id=1), make_event(event_id=2)]

        result = await list_events(
            limit=5,
            offset=10,
            service=service,
        )

        assert len(result) == 2
        service.list_events.assert_awaited_once_with(limit=5, offset=10)

    async def test_get_event_returns_single_event(self, make_event):
        session = AsyncMock()
        service = create_autospec(EventServices, instance=True)
        service.get_event.return_value = make_event(event_id=8, title="Festival")

        result = await get_event(
            event_id=8,
            service=service,
        )

        assert result.title == "Festival"
        service.get_event.assert_awaited_once_with(8)

    async def test_patch_event_commits_and_returns_updated_event(self, make_event):
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(EventServices, instance=True)
        service.event_update.return_value = make_event(event_id=3, title="Updated concert")

        result = await event_update(
            event_id=3,
            event_in=EventUpdate(title="Updated concert"),
            _=1,
            service=service,
            session=session,
        )

        assert result.title == "Updated concert"
        session.commit.assert_awaited_once()
        assert service.event_update.await_args.args[0] == 3
        assert service.event_update.await_args.args[1].title == "Updated concert"

    async def test_delete_event_commits_and_returns_204(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        service = create_autospec(EventServices, instance=True)

        result = await delete_event(
            event_id=12,
            _=1,
            session=session,
            service=service,
        )

        assert result is None
        service.delete_event.assert_awaited_once_with(12)
        session.commit.assert_awaited_once()
