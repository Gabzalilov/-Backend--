import asyncio
import html
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from uuid import UUID

from app.core.config import Settings
from app.models.schemas import AIAnalysis, ContactCreate

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_contact_notifications(
        self,
        *,
        contact_id: UUID,
        contact: ContactCreate,
        analysis: AIAnalysis,
    ) -> None:
        messages = self._build_messages(contact_id=contact_id, contact=contact, analysis=analysis)
        if self.settings.email_delivery_mode == "log":
            await asyncio.to_thread(self._write_to_outbox, contact_id, messages)
            return
        await asyncio.to_thread(self._send_smtp, messages)

    def _build_messages(
        self,
        *,
        contact_id: UUID,
        contact: ContactCreate,
        analysis: AIAnalysis,
    ) -> list[tuple[str, EmailMessage]]:
        safe_name = html.escape(contact.name)
        safe_phone = html.escape(contact.phone)
        safe_email = html.escape(str(contact.email))
        safe_comment = html.escape(contact.comment).replace("\n", "<br>")
        safe_summary = html.escape(analysis.summary)
        safe_reply = html.escape(analysis.suggested_reply)

        owner_html = f"""
        <h2>Новое обращение #{contact_id}</h2>
        <p><strong>Имя:</strong> {safe_name}<br>
        <strong>Телефон:</strong> {safe_phone}<br>
        <strong>Email:</strong> {safe_email}</p>
        <p><strong>Комментарий:</strong><br>{safe_comment}</p>
        <hr>
        <p><strong>AI-категория:</strong> {analysis.category.value}<br>
        <strong>Тональность:</strong> {analysis.sentiment.value}<br>
        <strong>Резюме:</strong> {safe_summary}<br>
        <strong>Источник:</strong> {analysis.source}</p>
        """
        owner = self._message(
            subject=f"Новое обращение: {analysis.category.value} — {contact.name}",
            recipient=self.settings.site_owner_email,
            html_body=owner_html,
            reply_to=str(contact.email),
        )

        user_html = f"""
        <h2>{safe_name}, обращение получено</h2>
        <p>{safe_reply}</p>
        <p><strong>Номер обращения:</strong> {contact_id}</p>
        <hr>
        <p style="color:#667085">Это автоматическая копия сообщения с сайта.</p>
        """
        user = self._message(
            subject="Мы получили ваше обращение",
            recipient=str(contact.email),
            html_body=user_html,
        )
        return [("owner", owner), ("user", user)]

    def _message(
        self,
        *,
        subject: str,
        recipient: str,
        html_body: str,
        reply_to: str | None = None,
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject.replace("\r", " ").replace("\n", " ")
        message["From"] = formataddr((self.settings.mail_from_name, self.settings.mail_from_email))
        message["To"] = recipient
        if reply_to:
            message["Reply-To"] = reply_to
        message.set_content("Для просмотра письма откройте HTML-версию.")
        message.add_alternative(html_body, subtype="html")
        return message

    def _write_to_outbox(self, contact_id: UUID, messages: list[tuple[str, EmailMessage]]) -> None:
        outbox: Path = self.settings.outbox_path
        outbox.mkdir(parents=True, exist_ok=True)
        for label, message in messages:
            path = outbox / f"{contact_id}-{label}.eml"
            path.write_bytes(message.as_bytes())
            logger.info("Email stored in local outbox | path=%s", path)

    def _send_smtp(self, messages: list[tuple[str, EmailMessage]]) -> None:
        with smtplib.SMTP(
            self.settings.smtp_host,
            self.settings.smtp_port,
            timeout=self.settings.smtp_timeout_seconds,
        ) as server:
            server.ehlo()
            if self.settings.smtp_use_tls:
                server.starttls()
                server.ehlo()
            if self.settings.smtp_username and self.settings.smtp_password:
                server.login(self.settings.smtp_username, self.settings.smtp_password)
            for _, message in messages:
                server.send_message(message)
