from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_reports_fallback_services(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ai"] == "fallback"
    assert response.json()["email"] == "local_outbox"
    assert response.headers["X-Request-ID"]


def test_contact_full_flow_uses_ai_fallback_and_writes_emails(
    client: TestClient,
    settings: Settings,
    valid_contact: dict[str, str],
) -> None:
    response = client.post("/api/contact", json=valid_contact)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert body["ai"]["source"] == "fallback"
    assert body["ai"]["category"] in {"project", "consultation"}
    assert response.headers["X-RateLimit-Remaining"] == "4"
    assert len(list(settings.outbox_path.glob("*.eml"))) == 2

    metrics = client.get(
        "/api/metrics",
        headers={"X-Metrics-Key": settings.metrics_api_key},
    )
    assert metrics.status_code == 200
    assert metrics.json()["total_contacts"] == 1
    assert metrics.json()["ai_fallbacks"] == 1
    assert metrics.json()["delivery"] == {"sent": 1}


def test_validation_errors_have_stable_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/contact",
        json={
            "name": "1",
            "phone": "123",
            "email": "not-an-email",
            "comment": "short",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["request_id"]
    assert {item["field"] for item in body["details"]} >= {
        "name",
        "phone",
        "email",
        "comment",
    }


def test_metrics_requires_key(client: TestClient) -> None:
    response = client.get("/api/metrics")

    assert response.status_code == 401
    assert response.json()["error"] == "metrics_unauthorized"


def test_email_failure_returns_503_and_is_visible_in_metrics(
    client: TestClient,
    settings: Settings,
    valid_contact: dict[str, str],
) -> None:
    async def unavailable_email(**_: object) -> None:
        raise OSError("SMTP is unavailable")

    client.app.state.container.email.send_contact_notifications = unavailable_email

    response = client.post("/api/contact", json=valid_contact)
    metrics = client.get(
        "/api/metrics",
        headers={"X-Metrics-Key": settings.metrics_api_key},
    )

    assert response.status_code == 503
    assert response.json()["error"] == "email_delivery_unavailable"
    assert metrics.json()["delivery"] == {"failed": 1}


def test_large_payload_is_rejected_before_parsing(client: TestClient) -> None:
    response = client.post(
        "/api/contact",
        content=b"x" * 33_000,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"] == "payload_too_large"


def test_rate_limit_returns_429(
    tmp_path: Path,
    valid_contact: dict[str, str],
) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_path=tmp_path / "limit.db",
        log_path=tmp_path / "limit.log",
        outbox_path=tmp_path / "outbox",
        cors_origins=["http://testserver"],
        ai_enabled=False,
        email_delivery_mode="log",
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
        rate_limit_salt="test-rate-limit-salt",
        metrics_api_key="test-metrics-key",
    )
    with TestClient(create_app(settings)) as limited_client:
        assert limited_client.post("/api/contact", json=valid_contact).status_code == 201
        blocked = limited_client.post("/api/contact", json=valid_contact)

    assert blocked.status_code == 429
    assert blocked.json()["error"] == "rate_limit_exceeded"
    assert int(blocked.headers["Retry-After"]) >= 1


def test_cors_allows_only_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/contact",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://testserver"


def test_openapi_contains_required_endpoint(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/contact" in response.json()["paths"]
