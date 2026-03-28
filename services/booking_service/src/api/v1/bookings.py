from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session

from src.core.dependencies import get_current_user_id

from src.schemas.booking import BookingCreate, BookingRead
from src.repositories.booking_repo import BookingRepository
from src.services.booking_service import BookingService


router = APIRouter(prefix="/bookings", tags=["Bookings"])


def get_booking_service(session: AsyncSession = Depends(get_async_session)) -> BookingService:
    """
    Фабрика сервиса.
    Сессия передаётся и в репозиторий и в сервис напрямую —
    потому что сервис использует сессию для SELECT FOR UPDATE.
    """
    repository = BookingRepository(session)
    return BookingService(repository, session)



@router.post(
    "/",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать бронирование"
)
async def booking_create(
    booking_in: BookingCreate,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    service: BookingService = Depends(get_booking_service)
):
    """
    Создаёт бронирование для текущего пользователя.
    Использует SELECT FOR UPDATE для защиты от Race Condition.
    Требует JWT токен в заголовке Authorization: Bearer <token>.
    """
    new_booking = await service.create(booking_data=booking_in, user_id=current_user_id )
    await session.commit()
    return new_booking


@router.get(
    "/my",
    response_model=list[BookingRead],
    summary="Мои бронирования"
)
async def get_my_bookings(
    service: BookingService = Depends(get_booking_service),
    current_user_id: int = Depends(get_current_user_id),
):
    """Возвращает все бронирования текущего пользователя."""
    return service.get_my_bookings(user_id=current_user_id)


@router.get(
    "/{booking_id: int}",
    response_model=BookingRead,
    summary="Получить бронирование по ID"
)
async def get_booking(
    booking_id: int,
    service: BookingService = Depends(get_booking_service),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Возвращает бронирование по ID.
    Возвращает 403 если бронирование принадлежит другому пользователю.
    """
    return service.get_booking(booking_id=booking_id, user_id=current_user_id)


@router.post(
    "/{booking_id: int}/cancel",
    response_model=BookingRead,
    summary="Отменить бронирование"
)
async def cancel_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_async_session),
    service: BookingService = Depends(get_booking_service),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Отменяет бронирование и возвращает билет в пул.
    Возвращает 403 если бронирование принадлежит другому пользователю.
    Возвращает 409 если бронирование уже отменено.
    """
    cancelled = await service.cancel_booking(booking_id, current_user_id)
    await session.commit()
    return cancelled