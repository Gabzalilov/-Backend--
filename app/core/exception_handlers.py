import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "Expected application error | request_id=%s code=%s",
            _request_id(request),
            exc.code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": exc.code,
                "message": exc.public_message,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = [str(part) for part in error["loc"] if part not in {"body", "query"}]
            details.append(
                {
                    "field": ".".join(location) or None,
                    "message": error["msg"],
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Проверьте заполнение полей",
                "request_id": _request_id(request),
                "details": details,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        phrase = (
            HTTPStatus(exc.status_code).phrase
            if exc.status_code in HTTPStatus._value2member_map_
            else "HTTP error"
        )
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": "http_error",
                "message": phrase,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error | request_id=%s", _request_id(request))
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Внутренняя ошибка сервиса",
                "request_id": _request_id(request),
            },
        )
