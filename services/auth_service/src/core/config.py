from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, SecretStr, computed_field


def _load_key_material(
    *,
    inline_value: SecretStr | None,
    path_value: str | None,
    setting_name: str,
) -> str:
    if inline_value:
        return inline_value.get_secret_value().replace("\\n", "\n")

    if path_value:
        return Path(path_value).read_text(encoding="utf-8")

    raise ValueError(f"{setting_name} must be provided via env value or file path")


class Settings(BaseSettings):
    APP_TITLE: str = Field(default="Auth Service")
    DEBUG: bool = Field(default=False)
    SQL_ECHO: bool = Field(default=False)

   
    POSTGRES_USER: str = Field(..., min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(...)
    POSTGRES_SERVER: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str = Field(..., min_length=1)

  
    ALGORITHM: str = Field(default="RS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)
    JWT_ISSUER: str = Field(default="booking-auth-service")
    JWT_PRIVATE_KEY: SecretStr | None = Field(default=None)
    JWT_PRIVATE_KEY_PATH: str | None = Field(default=None)
    JWT_PUBLIC_KEY: SecretStr | None = Field(default=None)
    JWT_PUBLIC_KEY_PATH: str | None = Field(default=None)

    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=300, ge=60, le=3600)
    LOGIN_RATE_LIMIT_BLOCK_SECONDS: int = Field(default=900, ge=60, le=86400)

  
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @computed_field
    @property
    def database_url(self) -> str:
        dsn = PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
        return str(dsn)

    @property
    def jwt_private_key(self) -> str:
        return _load_key_material(
            inline_value=self.JWT_PRIVATE_KEY,
            path_value=self.JWT_PRIVATE_KEY_PATH,
            setting_name="JWT_PRIVATE_KEY",
        )

    @property
    def jwt_public_key(self) -> str:
        return _load_key_material(
            inline_value=self.JWT_PUBLIC_KEY,
            path_value=self.JWT_PUBLIC_KEY_PATH,
            setting_name="JWT_PUBLIC_KEY",
        )


settings = Settings()
