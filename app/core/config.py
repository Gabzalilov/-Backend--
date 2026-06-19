from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Developer Portfolio API"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: Path = Path("data/app.db")
    log_path: Path = Path("logs/app.log")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"]
    )
    trust_proxy_headers: bool = False

    rate_limit_requests: int = Field(default=5, ge=1, le=1000)
    rate_limit_window_seconds: int = Field(default=3600, ge=1, le=86400)
    rate_limit_salt: str = Field(default="development-only-salt", min_length=8)

    ai_enabled: bool = True
    ai_provider: Literal["ollama"] = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "deepseek-r1:1.5b"
    ai_timeout_seconds: float = Field(default=120.0, gt=0, le=180)

    email_delivery_mode: Literal["log", "smtp"] = "log"
    site_owner_email: str = "owner@example.com"
    mail_from_email: str = "no-reply@example.com"
    mail_from_name: str = "Developer Portfolio"
    smtp_host: str = "smtp.example.com"
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    outbox_path: Path = Path("outbox")

    metrics_api_key: str = Field(default="development-metrics-key", min_length=8)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("smtp_username", "smtp_password", mode="before")
    @classmethod
    def empty_string_is_none(cls, value: object) -> object:
        return None if value == "" else value

    def ensure_runtime_directories(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.outbox_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
