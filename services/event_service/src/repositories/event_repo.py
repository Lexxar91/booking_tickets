from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.event import Event
from src.schemas.event import EventCreate, EventUpdate


class EventRepository:
    """Работает с мероприятиями в базе данных."""

    def __init__(self, session: AsyncSession):
        """Сохраняет сессию репозитория."""
        self.session = session

    async def create(self, event_data: EventCreate) -> Event:
        """Создает мероприятие в базе данных."""
        new_event = Event(**event_data.model_dump())
        self.session.add(new_event)

        await self.session.flush()
        await self.session.refresh(new_event)
        return new_event

    async def get_by_event_id(self, event_id: int) -> Event | None:
        """Ищет мероприятие по id."""
        stmt = select(Event).where(Event.id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_events(
            self,
            limit: int = 100,
            offset: int = 0) -> Sequence[Event]:
        """Возвращает список мероприятий."""
        stmt = select(Event).limit(limit).offset(offset)
        results = await self.session.execute(stmt)
        return results.scalars().all()

    async def event_update(
            self,
            event: Event,
            update_data: EventUpdate) -> Event:
        """Обновляет мероприятие в базе данных."""
        update_fields = update_data.model_dump(exclude_unset=True)

        for field, value in update_fields.items():
            setattr(event, field, value)

        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def event_delete(self, event: Event) -> None:
        """Удаляет мероприятие из базы данных."""
        await self.session.delete(event)
        await self.session.flush()
