from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.schemas.event import EventCreate, EventRead, EventUpdate
from src.repositories.event_repo import EventRepository
from src.services.event_service import EventServices


router = APIRouter(prefix="/events", tags=["Events"])


# --- Зависимость (Dependency) для сборки сервиса ---
def get_event_service(session: AsyncSession = Depends(get_async_session)) -> EventServices:
    """
    Фабрика для Dependency Injection.
    """
    repository = EventRepository(session)
    return EventServices(repository)


@router.post(
    "/",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новое мероприятие"
)
async def create_event(
    event_in: EventCreate,
    service: EventServices = Depends(get_event_service),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Создает новое мероприятие. 
    Транзакция коммитится только если бизнес-логика отработала без ошибок.
    """
    new_event = await service.create_event(event_in)
    await session.commit()
    return new_event


@router.get(
    "/{event_id}", 
    response_model=EventRead,
    summary="Получить мероприятие по ID"
)
async def get_event(
    event_id: int, 
    service: EventServices = Depends(get_event_service)
):
    """
    Возвращает данные мероприятия по его уникальному идентификатору.
    """
    return await service.get_event(event_id)



@router.get(
    "/",
    response_model=list[EventRead],
    summary="Получить список всех мероприятий"
)
async def list_events(
    limit: int = Query(10, ge=1, le=100, description="Сколько записей вернуть"),
    offset: int = Query(0, ge=0, description="Сколько записей пропустить"),
    service: EventServices = Depends(get_event_service)
):
    """Возвращает список мероприятий с поддержкой пагинации."""
    return await service.list_events(limit=limit, offset=offset)


@router.patch(
    "/{event_id}",
    response_model=EventRead,
    summary="Частично обновить мероприятие"
)
async def event_update(
    event_id: int,
    event_in: EventUpdate,
    service: EventServices = Depends(get_event_service),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Частично обновляет мероприятие (PATCH-семантика).
    Клиент передаёт только те поля, которые нужно изменить.
    Непереданные поля остаются без изменений.

    Возвращает 404 если мероприятие не найдено.
    """
    event_updated = await service.event_update(event_id, event_in)
    await session.commit()
    return event_updated


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить мероприятие"
)
async def delete_event(
    event_id: int,
    session: AsyncSession = Depends(get_async_session),
    service: EventServices = Depends(get_event_service),
):
    """
    Удаляет мероприятие по ID.

    Возвращает 204 No Content — стандарт REST для успешного удаления.
    Тело ответа пустое (возвращать нечего — объект удалён).
    Возвращает 404 если мероприятие не найдено.
    """
    await service.delete_event(event_id)
    await session.commit()
    



