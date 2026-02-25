from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "dev"
    api_key: str | None = None
    jwt_secret: str | None = None
    telegram_token: str | None = None
    telegram_admins: list[int] = Field(default_factory=list)
    telegram_operators: list[int] = Field(default_factory=list)
    redis_url: str | None = None
    log_level: str = "INFO"
    dashboard_origin: str | None = None
    gateway_url: str = "http://localhost:8000"
    binance_key: str | None = None
    binance_secret: str | None = None
    paper_starting_cash: float = 1000.0
    db_url: str | None = "sqlite:///mother_trades.db"
    webhook_url: str | None = None
    otlp_endpoint: str | None = None
    fernet_key: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="MOTHER_",
        env_file=".env",
        case_sensitive=False,
    )

    @field_validator("telegram_admins", "telegram_operators", mode="before")
    @classmethod
    def _split_ints(cls, value: object) -> list[int] | object:
        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",") if item.strip()]
            return [int(item) for item in parts]
        return value


settings = Settings()

