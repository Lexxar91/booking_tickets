from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, declared_attr
from typing import AsyncGenerator

from src.core.config import settings

#использовать класс как namespace
class DataBase:
    async_engine: AsyncEngine | None = None
    async_session: async_sessionmaker | None = None


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls):
        return cls.__name__.lower() + "s"
    

def init_engine(database_url: str) -> None:
    """Инициализация движка БД (вызывается в lifespan)"""
    
    DataBase.async_engine = create_async_engine(
        url=database_url,
        echo=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args = {
            "server_settings": {
                "application_name": "auth_service"
            },
    })

   

    DataBase.async_session = async_sessionmaker(
        DataBase.async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )

async def dispose_engine() -> None:
    """Закрытие движка БД (вызывается в lifespan)"""
    if DataBase.async_engine:
        await DataBase.async_engine.dispose()
        DataBase.async_engine = None
    

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Контекстный менеджер для получения сессии БД"""
    if not DataBase.async_session:
        raise RuntimeError("Database engine не инициализирован. Сначала вызовите init_engine.")
    
    async with DataBase.async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()



#Dependency Injection для FastAPI
# Каждый запрос получает свою изолированную сессию БД
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для инъекции сессии в эндпоинты"""
    async with get_db_session() as session:
        yield session


