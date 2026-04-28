from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import asyncio


from src.core.config import settings
from src.core.database import Base
from src.models.user import User  # noqa: F401
from src.models.refresh_token import RefreshToken  # noqa: F401
from src.models.login_attempt import LoginAttempt  # noqa: F401

# Alembic Config объект
config = context.config

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запускает миграции в offline-режиме."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        version_table_schema="auth",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Выполняет миграции на подключении."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="auth",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Запускает миграции в online-режиме."""
    from sqlalchemy import text

    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Создаём схему auth перед запуском миграций
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        await connection.commit()

        # run_sync нужен потому что Alembic синхронный,
        # а engine асинхронный — это мост между ними
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
