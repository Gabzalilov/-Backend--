import json

import httpx

from app.models.schemas import ContactCreate
from app.services.ai_service import AIService


async def test_deepseek_ollama_returns_structured_analysis() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        request_payload = json.loads(request.content)
        assert request_payload["model"] == "deepseek-r1:1.5b"
        assert request_payload["stream"] is False
        assert "sentiment" in request_payload["format"]["properties"]
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "sentiment": "positive",
                            "category": "project",
                            "summary": "Клиент хочет обсудить новый API.",
                            "suggested_reply": "Спасибо! Давайте обсудим детали проекта.",
                        },
                        ensure_ascii=False,
                    ),
                }
            },
        )

    service = AIService(
        enabled=True,
        base_url="http://ollama.test",
        model="deepseek-r1:1.5b",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    contact = ContactCreate(
        name="Анна",
        phone="+79991234567",
        email="anna@example.com",
        comment="Хочу обсудить разработку API для нового проекта.",
    )

    analysis = await service.analyze(contact)

    assert analysis.source == "deepseek"
    assert analysis.category.value == "project"
    assert analysis.sentiment.value == "positive"


async def test_deepseek_availability_checks_installed_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "deepseek-r1:1.5b"}]})

    service = AIService(
        enabled=True,
        base_url="http://ollama.test",
        model="deepseek-r1:1.5b",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )

    assert await service.is_available() is True


async def test_fallback_does_not_treat_development_as_job_offer() -> None:
    service = AIService(
        enabled=False,
        base_url="http://ollama.test",
        model="deepseek-r1:1.5b",
        timeout_seconds=5,
    )
    contact = ContactCreate(
        name="Ирина",
        phone="+79991234567",
        email="irina@example.com",
        comment="Нужна разработка нового API сервиса.",
    )

    analysis = await service.analyze(contact)

    assert analysis.source == "fallback"
    assert analysis.category.value == "project"
