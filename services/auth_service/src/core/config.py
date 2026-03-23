from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, SecretStr, computed_field


class Settings(BaseSettings):
    APP_TITLE: str = Field(default="Auth Service")
    DEBUG: bool = Field(default=False)

   
    POSTGRES_USER: str = Field(..., min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(...)
    POSTGRES_SERVER: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str = Field(..., min_length=1)

  
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

  
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


settings = Settings()