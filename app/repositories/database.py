from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    comment TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    category TEXT NOT NULL,
    ai_summary TEXT NOT NULL,
    ai_reply TEXT NOT NULL,
    ai_source TEXT NOT NULL CHECK (ai_source IN ('deepseek', 'fallback')),
    delivery_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (delivery_status IN ('pending', 'sent', 'failed')),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contacts_created_at ON contacts(created_at);
CREATE INDEX IF NOT EXISTS idx_contacts_category ON contacts(category);

CREATE TABLE IF NOT EXISTS rate_limits (
    fingerprint TEXT NOT NULL,
    route TEXT NOT NULL,
    window_started_at INTEGER NOT NULL,
    request_count INTEGER NOT NULL,
    PRIMARY KEY (fingerprint, route)
);
"""

MIGRATE_AI_SOURCE = """
BEGIN IMMEDIATE;
DROP INDEX IF EXISTS idx_contacts_created_at;
DROP INDEX IF EXISTS idx_contacts_category;
ALTER TABLE contacts RENAME TO contacts_legacy;

CREATE TABLE contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    comment TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    category TEXT NOT NULL,
    ai_summary TEXT NOT NULL,
    ai_reply TEXT NOT NULL,
    ai_source TEXT NOT NULL CHECK (ai_source IN ('deepseek', 'fallback')),
    delivery_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (delivery_status IN ('pending', 'sent', 'failed')),
    created_at TEXT NOT NULL
);

INSERT INTO contacts (
    id, name, phone, email, comment, sentiment, category, ai_summary,
    ai_reply, ai_source, delivery_status, created_at
)
SELECT
    id, name, phone, email, comment, sentiment, category, ai_summary,
    ai_reply,
    CASE WHEN ai_source = 'deepseek' THEN 'deepseek' ELSE 'fallback' END,
    delivery_status, created_at
FROM contacts_legacy;
DROP TABLE contacts_legacy;
CREATE INDEX idx_contacts_created_at ON contacts(created_at);
CREATE INDEX idx_contacts_category ON contacts(category);
COMMIT;
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        connection = await aiosqlite.connect(self.path, timeout=10)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys = ON")
        await connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            await connection.close()

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self.connect() as connection:
            await connection.execute("PRAGMA journal_mode = WAL")
            await connection.executescript(SCHEMA)
            cursor = await connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'contacts'"
            )
            contacts_schema = (await cursor.fetchone())["sql"]
            if "'deepseek'" not in contacts_schema:
                await connection.executescript(MIGRATE_AI_SOURCE)
            await connection.commit()

    async def ping(self) -> bool:
        try:
            async with self.connect() as connection:
                cursor = await connection.execute("SELECT 1")
                return (await cursor.fetchone())[0] == 1
        except (aiosqlite.Error, OSError):
            return False
