import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

TrimmedName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Comment = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RequestCategory(StrEnum):
    PROJECT = "project"
    CONSULTATION = "consultation"
    JOB_OFFER = "job_offer"
    SUPPORT = "support"
    OTHER = "other"


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: TrimmedName
    phone: str = Field(min_length=7, max_length=30, examples=["+7 (999) 123-45-67"])
    email: EmailStr
    comment: Comment

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if any(character in value for character in "\r\n\t<>"):
            raise ValueError("имя содержит недопустимые символы")
        if not any(character.isalpha() for character in value):
            raise ValueError("имя должно содержать буквы")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[+\d\s().-]+", value):
            raise ValueError("телефон содержит недопустимые символы")
        digits = re.sub(r"\D", "", value)
        if not 10 <= len(digits) <= 15:
            raise ValueError("телефон должен содержать от 10 до 15 цифр")
        return f"+{digits}" if value.startswith("+") else digits


class AIAnalysis(BaseModel):
    sentiment: Sentiment
    category: RequestCategory
    summary: str = Field(min_length=1, max_length=240)
    suggested_reply: str = Field(min_length=1, max_length=700)
    source: Literal["deepseek", "fallback"] = "deepseek"


class ContactAccepted(BaseModel):
    request_id: str
    status: Literal["accepted"] = "accepted"
    message: str = "Обращение принято. Копия отправлена на вашу почту."
    ai: AIAnalysis


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: Literal["ok", "unavailable"]
    ai: Literal["configured", "fallback"]
    ai_provider: Literal["deepseek_ollama"]
    ai_model: str
    email: Literal["smtp", "local_outbox"]
    timestamp: datetime


class MetricsResponse(BaseModel):
    generated_at: datetime
    total_contacts: int
    contacts_today: int
    ai_fallbacks: int
    delivery: dict[str, int]
    categories: dict[str, int]
    sentiments: dict[str, int]


class ErrorItem(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: str
    details: list[ErrorItem] | None = None
