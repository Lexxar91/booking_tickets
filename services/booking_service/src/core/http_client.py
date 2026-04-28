import httpx
from fastapi import HTTPException, status

from src.core.config import settings


async def get_event(event_id: int) -> dict:
    """Возвращает данные для event."""

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{settings.EVENT_SERVICE_URL}/api/v1/events/{event_id}"
            )

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Мероприятие с id={event_id} не найдено"
            )

        response.raise_for_status()
        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event Service недоступен (timeout)"
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Сервис мероприятий недоступен. "
                "Проверьте подключение или попробуйте позже."
            ),
        )
