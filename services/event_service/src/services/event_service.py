from typing import Sequence

from fastapi import HTTPException, status

from src.core.metrics import (
    decrement_total_events,
    increment_total_events,
    track_event_created,
    track_event_deleted,
    track_event_updated,
)
from src.models.event import Event
from src.repositories.event_repo import EventRepository
from src.schemas.event import EventCreate, EventUpdate


class EventServices:
    """
    Слой бизнес-логики.
    Сервис не работает с сессией БД напрямую, он использует репозиторий.
    """

    def __init__(self, repository: EventRepository):
        self.repository = repository

    async def create_event(self, event_data: EventCreate) -> Event:
        """
        Бизнес-логика создания мероприятия.
        Здесь могли бы быть доп. проверки, например:
        """
        event = await self.repository.create(event_data)
        track_event_created()
        increment_total_events()
        return event

    async def get_event(self, event_id: int) -> Event:
        """
        Получение мероприятия с проверкой на существование.
        
        Raises:
            HTTPException 404: Если запись не найдена.
        """
        event = await self.repository.get_by_event_id(event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Объект Event с id {event_id} не найден",
            )
        return event

    async def list_events(self, limit: int, offset: int) -> Sequence[Event]:
        """Получение списка мероприятий."""
        return await self.repository.get_all_events(limit=limit, offset=offset)

    async def event_update(self, event_id: int, update_data: EventUpdate) -> Event:
        """
        Частичное обновление мероприятия.
        Сначала проверяем что оно существует, потом обновляем.

        Raises:
            HTTPException 404: Если мероприятие не найдено.
        """
        event = await self.get_event(event_id)
        track_event_updated()
        return await self.repository.event_update(event, update_data)

    async def delete_event(self, event_id: int) -> None:
        """
        Удаление мероприятия.

        Raises:
            HTTPException 404: Если мероприятие не найдено.
        """
        event = await self.get_event(event_id)
        await self.repository.event_delete(event)
        track_event_deleted()
        decrement_total_events()
