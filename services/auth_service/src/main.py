import datetime
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.auth import router as auth_router
from src.api.v1.bff import router as bff_router
from src.core.config import settings
from src.core.database import (dispose_engine, get_async_session,
                               get_db_session, init_engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Управляет подключениями БД и HTTP-клиентом BFF."""
    print(f"INFO: Service '{settings.APP_TITLE}' is starting up...")

    try:
        init_engine(settings.database_url)
        print("INFO: Database engine initialized successfully")

        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            print("INFO: Database connection verified")

    except Exception as e:
        print(f"CRITICAL: Failed to initialize database: {e}")
        raise

    async with httpx.AsyncClient(
        timeout=5, follow_redirects=False, trust_env=False,
    ) as client:
        app.state.bff_http_client = client
        yield

    print(f"INFO:     Service '{settings.APP_TITLE}' is shutting down...")

    try:
        await dispose_engine()
        print("INFO: Database connections closed gracefully")

    except Exception as e:
        print(f"ERROR: Failed to close database connections: {e}")


app = FastAPI(
    title=settings.APP_TITLE,
    debug=settings.DEBUG,
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(bff_router)


@app.middleware("http")
async def disable_browser_cache(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Запрещает кэшировать ответы BFF, включая ошибки авторизации."""
    response = await call_next(request)
    if request.url.path.startswith("/bff/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get('/health', status_code=status.HTTP_200_OK)
async def check_health(session: AsyncSession = Depends(get_async_session)):
    """Проверяет доступность сервиса и базы данных."""

    try:
        await session.execute(text('SELECT 1'))
        return {
            "status": "ok",
            "service": settings.APP_TITLE,
            "database": "connected",
            "date": datetime.datetime.now(datetime.timezone.utc),
        }

    except Exception as e:
        print(f"CRITICAL: Database connection failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
