from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import DeclarativeBase, declared_attr
from src.core.config import settings


class DataBase:
    """Хранит общий движок и фабрику сессий."""
    async_engine: AsyncEngine | None = None
    async_session: async_sessionmaker | None = None


class Base(DeclarativeBase):
    """Задает базу для SQLAlchemy-моделей."""

    @declared_attr.directive
    def __tablename__(cls):
        """Возвращает имя таблицы для модели."""
        return cls.__name__.lower() + "s"


def init_engine(database_url: str) -> None:
    """Инициализирует движок базы данных."""

    DataBase.async_engine = create_async_engine(
        url=database_url,
        echo=settings.SQL_ECHO,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={
            "server_settings": {
                "application_name": settings.APP_TITLE
            },
        })

    DataBase.async_session = async_sessionmaker(
        DataBase.async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )


async def dispose_engine() -> None:
    """Закрывает движок базы данных."""
    if DataBase.async_engine:
        await DataBase.async_engine.dispose()
        DataBase.async_engine = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Выдает сессию базы данных."""
    if not DataBase.async_session:
        raise RuntimeError(
            "Database engine не инициализирован. "
            "Сначала вызовите init_engine."
        )

    async with DataBase.async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Выдает сессию для Depends."""
    async with get_db_session() as session:
        yield session
