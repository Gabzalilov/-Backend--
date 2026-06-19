from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import Container, get_container, verify_metrics_key
from app.models.schemas import HealthResponse, MetricsResponse

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="Проверить состояние сервиса")
async def health(
    container: Annotated[Container, Depends(get_container)],
) -> HealthResponse:
    database_ok = await container.database.ping()
    ai_available = await container.ai.is_available()
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        version="1.0.0",
        database="ok" if database_ok else "unavailable",
        ai="configured" if ai_available else "fallback",
        ai_provider="deepseek_ollama",
        ai_model=container.ai.model,
        email="smtp" if container.settings.email_delivery_mode == "smtp" else "local_outbox",
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Получить статистику обращений",
    dependencies=[Depends(verify_metrics_key)],
)
async def metrics(
    container: Annotated[Container, Depends(get_container)],
) -> MetricsResponse:
    return await container.contacts.metrics()
