from datetime import UTC, datetime
from uuid import UUID

from app.models.schemas import AIAnalysis, ContactCreate, MetricsResponse
from app.repositories.database import Database


class ContactRepository:
    def __init__(self, database: Database):
        self.database = database

    async def create(self, contact_id: UUID, payload: ContactCreate, analysis: AIAnalysis) -> None:
        async with self.database.connect() as connection:
            await connection.execute(
                """
                INSERT INTO contacts (
                    id, name, phone, email, comment, sentiment, category,
                    ai_summary, ai_reply, ai_source, delivery_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    str(contact_id),
                    payload.name,
                    payload.phone,
                    str(payload.email),
                    payload.comment,
                    analysis.sentiment.value,
                    analysis.category.value,
                    analysis.summary,
                    analysis.suggested_reply,
                    analysis.source,
                    datetime.now(UTC).isoformat(),
                ),
            )
            await connection.commit()

    async def set_delivery_status(self, contact_id: UUID, status: str) -> None:
        async with self.database.connect() as connection:
            await connection.execute(
                "UPDATE contacts SET delivery_status = ? WHERE id = ?",
                (status, str(contact_id)),
            )
            await connection.commit()

    async def metrics(self) -> MetricsResponse:
        async with self.database.connect() as connection:
            total_cursor = await connection.execute("SELECT COUNT(*) FROM contacts")
            today_cursor = await connection.execute(
                "SELECT COUNT(*) FROM contacts WHERE date(created_at) = date('now')"
            )
            fallback_cursor = await connection.execute(
                "SELECT COUNT(*) FROM contacts WHERE ai_source = 'fallback'"
            )
            delivery_cursor = await connection.execute(
                "SELECT delivery_status, COUNT(*) AS count FROM contacts GROUP BY delivery_status"
            )
            category_cursor = await connection.execute(
                "SELECT category, COUNT(*) AS count FROM contacts GROUP BY category"
            )
            sentiment_cursor = await connection.execute(
                "SELECT sentiment, COUNT(*) AS count FROM contacts GROUP BY sentiment"
            )

            total = (await total_cursor.fetchone())[0]
            today = (await today_cursor.fetchone())[0]
            fallbacks = (await fallback_cursor.fetchone())[0]
            delivery = {
                row["delivery_status"]: row["count"] for row in await delivery_cursor.fetchall()
            }
            categories = {row["category"]: row["count"] for row in await category_cursor.fetchall()}
            sentiments = {
                row["sentiment"]: row["count"] for row in await sentiment_cursor.fetchall()
            }

        return MetricsResponse(
            generated_at=datetime.now(UTC),
            total_contacts=total,
            contacts_today=today,
            ai_fallbacks=fallbacks,
            delivery=delivery,
            categories=categories,
            sentiments=sentiments,
        )
