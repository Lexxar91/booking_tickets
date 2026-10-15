"""BFF для браузера: cookie-сессия, CSRF и ограниченное проксирование API."""

from datetime import datetime, timezone
from re import fullmatch

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.auth import _get_client_ip, get_auth_service
from src.api.v1.auth import register as register_user
from src.core.config import settings
from src.core.database import get_async_session
from src.models.browser_session import BrowserSession
from src.schemas.browser_session import BrowserSessionRead
from src.schemas.user import UserRead, UserRegister
from src.services.auth_service import AuthService
from src.services.browser_session_service import (COOKIE_NAME,
                                                  BrowserSessionService)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def verify_origin(request: Request) -> None:
    """Запрещает изменяющие запросы из чужого origin, включая login CSRF."""
    if request.method not in SAFE_METHODS:
        if (
            request.headers.get("origin") not in settings.BFF_ALLOWED_ORIGINS
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            raise HTTPException(403, "Недопустимый Origin")


router = APIRouter(
    prefix="/bff", tags=["Browser"], dependencies=[Depends(verify_origin)],
)


def get_browser_service(
    session: AsyncSession = Depends(get_async_session),
    auth: AuthService = Depends(get_auth_service),
) -> BrowserSessionService:
    """Собирает BFF на общей транзакции с AuthService."""
    return BrowserSessionService(session, auth)


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Возвращает HTTP-клиент из lifespan приложения."""
    return request.app.state.bff_http_client


async def get_browser_session(
    request: Request,
    service: BrowserSessionService = Depends(get_browser_service),
) -> BrowserSession:
    """Блокирует cookie-сессию и проверяет CSRF изменяющих запросов."""
    return await service.get(
        request.cookies.get(COOKIE_NAME),
        request.headers.get("x-csrf-token"),
        require_csrf=request.method not in SAFE_METHODS,
    )


@router.post("/auth/register", response_model=UserRead, status_code=201)
async def browser_register(
    user_in: UserRegister,
    session: AsyncSession = Depends(get_async_session),
    auth: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Регистрирует пользователя после проверки Origin."""
    user = await register_user(user_in, session, auth)
    return UserRead.model_validate(user)


@router.post("/auth/login", response_model=BrowserSessionRead)
async def browser_login(
    request: Request,
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    service: BrowserSessionService = Depends(get_browser_service),
) -> dict[str, object]:
    """Фиксирует серверную сессию и выдает HttpOnly-cookie вместо JWT."""
    try:
        session_id, browser = await service.create(
            form.username, form.password, _get_client_ip(request))
    except HTTPException:
        # Неудачные попытки входа должны сохраняться для rate limiting.
        await service.session.commit()
        raise
    old_id = request.cookies.get(COOKIE_NAME)
    if old_id:
        try:
            old_browser = await service.get(old_id)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
        else:
            await service.revoke(old_browser)
    data = await service.public_data(browser)
    await service.session.commit()
    response.set_cookie(
        COOKIE_NAME, session_id, secure=True, httponly=True, samesite="strict",
        path="/", max_age=max(0, int((
            browser.expires_at - datetime.now(timezone.utc)).total_seconds())),
    )
    return data


@router.get("/auth/session", response_model=BrowserSessionRead)
async def browser_session(
    browser: BrowserSession = Depends(get_browser_session),
    service: BrowserSessionService = Depends(get_browser_service),
) -> dict[str, object]:
    """Восстанавливает пользователя после перезагрузки без передачи JWT."""
    await service.refresh(browser)
    data = await service.public_data(browser)
    await service.session.commit()
    return data


@router.post("/auth/refresh", response_model=BrowserSessionRead)
async def browser_refresh(
    browser: BrowserSession = Depends(get_browser_session),
    service: BrowserSessionService = Depends(get_browser_service),
) -> dict[str, object]:
    """Принудительно обновляет JWT на сервере после проверки CSRF."""
    await service.refresh(browser, force=True)
    data = await service.public_data(browser)
    await service.session.commit()
    return data


@router.post("/auth/logout", status_code=204)
async def browser_logout(
    response: Response,
    browser: BrowserSession = Depends(get_browser_session),
    service: BrowserSessionService = Depends(get_browser_service),
) -> None:
    """Отзывает refresh-токен, удаляет запись и cookie браузера."""
    await service.revoke(browser)
    await service.session.commit()
    response.delete_cookie(
        COOKIE_NAME, path="/", secure=True, httponly=True, samesite="strict",
    )


async def forward(
    request: Request, client: httpx.AsyncClient, url: str,
    access_token: str | None = None,
) -> Response:
    """Передает запрос фиксированному API без cookie и заголовков клиента."""
    headers = {"content-type": request.headers.get(
        "content-type", "application/json")}
    if access_token:
        headers["authorization"] = f"Bearer {access_token}"
    try:
        outgoing = client.build_request(
            request.method, url, params=request.query_params.multi_items(),
            content=await request.body(), headers=headers,
        )
        # Общий HTTP-клиент не должен пересылать накопленные cookie сервисов.
        outgoing.headers.pop("cookie", None)
        upstream = await client.send(outgoing, follow_redirects=False)
    except httpx.RequestError:
        raise HTTPException(503, "Сервис временно недоступен") from None
    # Не передаем redirect: браузер не должен обходить BFF по Location.
    if upstream.is_redirect:
        raise HTTPException(502, "Неожиданный redirect сервиса")
    response_headers = {
        name: upstream.headers[name]
        for name in ("content-type", "retry-after")
        if name in upstream.headers
    }
    return Response(upstream.content, upstream.status_code,
                    headers=response_headers)


@router.api_route("/events/", methods=["GET", "POST"])
@router.api_route("/events/{event_id}", methods=["GET", "PATCH", "DELETE"])
async def browser_events(
    request: Request,
    event_id: int | None = None,
    service: BrowserSessionService = Depends(get_browser_service),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Response:
    """Проксирует каталог; изменение требует cookie-сессию и CSRF."""
    access_token = None
    if request.method != "GET":
        browser = await get_browser_session(request, service)
        await service.refresh(browser)
        access_token = service.decrypt(browser.access_token)
    await service.session.commit()
    suffix = "" if event_id is None else str(event_id)
    return await forward(
        request, client,
        f"{settings.EVENT_SERVICE_URL}/api/v1/events/{suffix}", access_token)


@router.api_route("/bookings/{booking_path:path}", methods=["GET", "POST"])
async def browser_bookings(
    request: Request,
    booking_path: str,
    browser: BrowserSession = Depends(get_browser_session),
    service: BrowserSessionService = Depends(get_browser_service),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Response:
    """Проксирует только известные пути бронирований с серверным JWT."""
    allowed = (r"(?:my|[0-9]+)" if request.method == "GET"
               else r"(?:[0-9]+/cancel)?")
    if fullmatch(allowed, booking_path) is None:
        raise HTTPException(404, "Неизвестный путь бронирования")
    await service.refresh(browser)
    access_token = service.decrypt(browser.access_token)
    await service.session.commit()
    return await forward(
        request, client,
        f"{settings.BOOKING_SERVICE_URL}/api/v1/bookings/{booking_path}",
        access_token,
    )
