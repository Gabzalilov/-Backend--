import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("app.requests")


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_body_bytes: int = 32_768):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", "").strip()[:100] or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        content_length = request.headers.get("content-length")
        body_is_too_large = (
            content_length
            and content_length.isdigit()
            and int(content_length) > self.max_body_bytes
        )
        if body_is_too_large:
            response: Response = JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "message": "Тело запроса превышает допустимый размер",
                    "request_id": request_id,
                },
            )
        else:
            response = await call_next(request)

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
