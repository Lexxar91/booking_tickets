from typing import Sequence

from fastapi import HTTPException, status
from src.core.metrics import (decrement_total_events, increment_total_events,
                              track_event_created, track_event_deleted,
                              track_event_updated)
from src.models.event import Event
from src.repositories.event_repo import EventRepository
from src.schemas.event import EventCreate, EventUpdate


class EventServices:
    """Содержит бизнес-логику мероприятий."""

    def __init__(self, repository: EventRepository):
        """Сохраняет зависимости сервиса."""
        self.repository = repository

    async def create_event(self, event_data: EventCreate) -> Event:
        """Создает новое мероприятие."""
        event = await self.repository.create(event_data)
        track_event_created()
        increment_total_events()
        return event

    async def get_event(self, event_id: int) -> Event:
        """Возвращает мероприятие по id."""
        event = await self.repository.get_by_event_id(event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Объект Event с id {event_id} не найден",
            )
        return event

    async def list_events(self, limit: int, offset: int) -> Sequence[Event]:
        """Возвращает список мероприятий."""
        return await self.repository.get_all_events(limit=limit, offset=offset)

    async def event_update(
        self,
        event_id: int,
        update_data: EventUpdate,
    ) -> Event:
        """Обновляет существующее мероприятие."""
        event = await self.get_event(event_id)
        track_event_updated()
        return await self.repository.event_update(event, update_data)

    async def delete_event(self, event_id: int) -> None:
        """Удаляет мероприятие по id."""
        event = await self.get_event(event_id)
        await self.repository.event_delete(event)
        track_event_deleted()
        decrement_total_events()
