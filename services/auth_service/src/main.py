import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import dispose_engine, get_async_session, get_db_session, init_engine
from src.core.config import settings

from src.api.v1.auth import router as auth_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Асинхронный менеджер контекста для управления жизненным циклом приложения.
    
    Args:
        app (FastAPI): Экземпляр приложения FastAPI.
        
    Yields:
        None: Управление передается приложению.
        
    """
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


app.include_router(auth_router, prefix="/api/v1")


@app.get('/health', status_code=status.HTTP_200_OK)
async def check_health(session: AsyncSession = Depends(get_async_session)):
    """
    Args:
        session (AsyncSession): Сессия БД, внедряемая через Depends.
                                FastAPI автоматически создаст сессию и передаст её сюда.

    Returns:
        dict: Статус сервиса и БД.
    
    Raises:
        HTTPException (503): Если база данных недоступна. 
                             Код 503 (Service Unavailable) скажет Kubernetes перезагрузить под.
    """

    try:
        await session.execute(text('SELECT 1'))
        return {
            "status": "ok",
            "service": settings.APP_TITLE,
            "database": "connected",
            "date": datetime.datetime.now(datetime.timezone.utc)
        }

    except Exception as e:
        print(f"CRITICAL: Database connection failed: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )