from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.contact import router as contact_router
from app.api.dependencies import build_container
from app.api.system import router as system_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.ensure_runtime_directories()
    configure_logging(settings.log_path, debug=settings.debug)
    container = build_container(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await container.database.initialize()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "API для формы обратной связи: валидация, AI-классификация, "
            "email-уведомления, rate limiting и метрики."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "X-Metrics-Key"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(contact_router)
    app.include_router(system_router)

    static_path = Path(__file__).resolve().parent.parent / "static"
    if static_path.exists():
        app.mount("/", StaticFiles(directory=static_path, html=True), name="frontend")
    return app


app = create_app()
