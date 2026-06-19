import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request, Response

from app.core.config import Settings
from app.core.errors import MetricsUnauthorized, RateLimitExceeded
from app.repositories.contact_repository import ContactRepository
from app.repositories.database import Database
from app.repositories.rate_limit_repository import RateLimitRepository
from app.services.ai_service import AIService
from app.services.contact_service import ContactService
from app.services.email_service import EmailService


@dataclass
class Container:
    settings: Settings
    database: Database
    contacts: ContactRepository
    rate_limits: RateLimitRepository
    ai: AIService
    email: EmailService
    contact_service: ContactService


def build_container(settings: Settings) -> Container:
    database = Database(settings.database_path)
    contacts = ContactRepository(database)
    rate_limits = RateLimitRepository(database)
    ai = AIService(
        enabled=settings.ai_enabled,
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    email = EmailService(settings)
    contact_service = ContactService(repository=contacts, ai_service=ai, email_service=email)
    return Container(
        settings=settings,
        database=database,
        contacts=contacts,
        rate_limits=rate_limits,
        ai=ai,
        email=email,
        contact_service=contact_service,
    )


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_contact_rate_limit(
    request: Request,
    response: Response,
    container: Annotated[Container, Depends(get_container)],
) -> None:
    settings = container.settings
    client_ip = get_client_ip(request, settings)
    fingerprint = hmac.new(
        settings.rate_limit_salt.encode(),
        client_ip.encode(),
        hashlib.sha256,
    ).hexdigest()
    allowed, remaining, retry_after = await container.rate_limits.consume(
        fingerprint=fingerprint,
        route="POST:/api/contact",
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    headers = {
        "X-RateLimit-Limit": str(settings.rate_limit_requests),
        "X-RateLimit-Remaining": str(remaining),
        "Retry-After": str(retry_after),
    }
    if not allowed:
        raise RateLimitExceeded(headers=headers)
    response.headers.update(headers)


def verify_metrics_key(
    container: Annotated[Container, Depends(get_container)],
    x_metrics_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = container.settings.metrics_api_key
    if x_metrics_key is None or not secrets.compare_digest(x_metrics_key, expected):
        raise MetricsUnauthorized(headers={"WWW-Authenticate": "X-Metrics-Key"})
