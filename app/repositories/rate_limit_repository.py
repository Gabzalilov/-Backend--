import time

from app.repositories.database import Database


class RateLimitRepository:
    """Atomic fixed-window rate limiting persisted in SQLite."""

    def __init__(self, database: Database):
        self.database = database

    async def consume(
        self,
        *,
        fingerprint: str,
        route: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        now = int(time.time())
        window_start = now - (now % window_seconds)
        retry_after = window_start + window_seconds - now

        async with self.database.connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            await connection.execute(
                """
                INSERT INTO rate_limits (fingerprint, route, window_started_at, request_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(fingerprint, route) DO UPDATE SET
                    window_started_at = CASE
                        WHEN rate_limits.window_started_at < excluded.window_started_at
                        THEN excluded.window_started_at
                        ELSE rate_limits.window_started_at
                    END,
                    request_count = CASE
                        WHEN rate_limits.window_started_at < excluded.window_started_at THEN 1
                        ELSE rate_limits.request_count + 1
                    END
                """,
                (fingerprint, route, window_start),
            )
            cursor = await connection.execute(
                "SELECT request_count FROM rate_limits WHERE fingerprint = ? AND route = ?",
                (fingerprint, route),
            )
            count = (await cursor.fetchone())[0]
            await connection.commit()

        remaining = max(0, limit - count)
        return count <= limit, remaining, max(1, retry_after)
