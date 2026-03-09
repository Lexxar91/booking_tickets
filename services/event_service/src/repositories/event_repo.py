from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event
from src.schemas.event import EventCreate, EventUpdate


class EventRepository:
    """
    Репозиторий для сущности Event.
    Инкапсулирует все SQL запросы (CRUD операции) к таблице events.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event_data: EventCreate) -> Event:
        """
        Создает новую запись мероприятия в базе данных.
        
        Args:
            event_data (EventCreate): Провалидированные данные от пользователя.
        Returns:
            Event: Объект модели SQLAlchemy (с уже присвоенным ID).
        """
        new_event = Event(**event_data.model_dump())
        self.session.add(new_event)

        await self.session.flush()
        await self.session.refresh(new_event)
        return new_event
    
    async def get_by_event_id(self, event_id: int) -> Event | None:
        """
        Ищет мероприятие по его ID.
        
        Returns:
            Event | None: Возвращает модель, если найдена, иначе None.
        """
        stmt = select(Event).where(Event.id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_events(self, limit: int = 100, offset: int = 0) -> Sequence[Event]:
        """
        Возвращает список мероприятий с пагинацией (limit/offset).
        """
        stmt = select(Event).limit(limit).offset(offset)
        results = await self.session.execute(stmt)
        return results.scalars().all()
    
    async def event_update(self, event: Event, update_data: EventUpdate) -> Event:
        """
        Частичное обновление мероприятия (PATCH-семантика).

        model_dump(exclude_unset=True) — ключевой момент:
        возвращает только те поля, которые клиент явно передал в запросе.
        Если клиент передал {"title": "Новое название"}, то только title
        и будет обновлён. Остальные поля останутся нетронутыми.

        Без exclude_unset=True все None-поля перезаписали бы данные в БД.
        """
        update_fields = update_data.model_dump(exclude_unset=True)

        for field, value in update_fields.items():
            setattr(event, field, value)

        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def event_delete(self, event: Event) -> None:
        """
        Удаляет мероприятие из базы данных.
        После flush() объект помечается как удалённый в рамках транзакции.
        Физически строка удалится только после commit() в роутере.
        """
        await self.session.delete(event)
        await self.session.flush()
