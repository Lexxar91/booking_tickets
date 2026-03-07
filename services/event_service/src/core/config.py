from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, SecretStr, computed_field
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class Settings(BaseSettings):
    APP_TITLE: str = Field(default="Event Service", min_length=1)
    DEBUG: bool = Field(default=False)

    POSTGRES_USER: str = Field(..., min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(...) # Секрет!
    POSTGRES_SERVER: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str = Field(..., min_length=1)

    # Production настройки
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" # Игнорировать лишние переменные в .env
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Безопасное формирование DSN"""
        dsn = PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

        return str(dsn)


settings = Settings()