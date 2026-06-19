from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import Container, enforce_contact_rate_limit, get_container
from app.models.schemas import ContactAccepted, ContactCreate, ErrorResponse

router = APIRouter(prefix="/api", tags=["Contact"])


@router.post(
    "/contact",
    response_model=ContactAccepted,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить обращение",
    description=(
        "Валидирует форму, анализирует комментарий с AI, сохраняет обращение "
        "и отправляет уведомления владельцу и пользователю."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Ошибка валидации"},
        429: {"model": ErrorResponse, "description": "Превышен лимит запросов"},
        503: {"model": ErrorResponse, "description": "Почтовый сервис недоступен"},
    },
    dependencies=[Depends(enforce_contact_rate_limit)],
)
async def create_contact(
    payload: ContactCreate,
    container: Annotated[Container, Depends(get_container)],
) -> ContactAccepted:
    return await container.contact_service.submit(payload)
