import logging
from uuid import uuid4

from app.core.errors import EmailDeliveryError
from app.models.schemas import ContactAccepted, ContactCreate
from app.repositories.contact_repository import ContactRepository
from app.services.ai_service import AIService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class ContactService:
    def __init__(
        self,
        *,
        repository: ContactRepository,
        ai_service: AIService,
        email_service: EmailService,
    ):
        self.repository = repository
        self.ai_service = ai_service
        self.email_service = email_service

    async def submit(self, payload: ContactCreate) -> ContactAccepted:
        analysis = await self.ai_service.analyze(payload)
        contact_id = uuid4()
        await self.repository.create(contact_id, payload, analysis)

        try:
            await self.email_service.send_contact_notifications(
                contact_id=contact_id,
                contact=payload,
                analysis=analysis,
            )
            await self.repository.set_delivery_status(contact_id, "sent")
        except Exception as exc:
            await self.repository.set_delivery_status(contact_id, "failed")
            logger.exception("Email delivery failed | contact_id=%s", contact_id)
            raise EmailDeliveryError() from exc

        logger.info(
            "Contact accepted | contact_id=%s category=%s sentiment=%s ai_source=%s",
            contact_id,
            analysis.category.value,
            analysis.sentiment.value,
            analysis.source,
        )
        return ContactAccepted(request_id=str(contact_id), ai=analysis)
