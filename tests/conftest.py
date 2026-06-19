from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_path=tmp_path / "data" / "test.db",
        log_path=tmp_path / "logs" / "test.log",
        outbox_path=tmp_path / "outbox",
        cors_origins=["http://testserver"],
        ai_enabled=False,
        email_delivery_mode="log",
        rate_limit_requests=5,
        rate_limit_window_seconds=60,
        rate_limit_salt="test-rate-limit-salt",
        metrics_api_key="test-metrics-key",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_contact() -> dict[str, str]:
    return {
        "name": "Анна Смирнова",
        "phone": "+7 (999) 123-45-67",
        "email": "anna@example.com",
        "comment": "Нужен новый API для проекта и консультация по архитектуре.",
    }
