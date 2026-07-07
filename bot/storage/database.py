"""SQLite database for persistent transcript cache and group settings."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import aiosqlite

from bot.config import settings
from bot.storage.sqlite_retry import with_sqlite_retry

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    voice_message_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    UNIQUE (chat_id, voice_message_id)
);

CREATE INDEX IF NOT EXISTS idx_transcripts_expires
    ON transcripts (expires_at);

CREATE TABLE IF NOT EXISTS group_settings (
    chat_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    whisper_model TEXT NOT NULL DEFAULT 'medium',
    llm_model TEXT NOT NULL DEFAULT 'qwen2.5-3b',
    language TEXT NOT NULL DEFAULT 'auto',
    ui_language TEXT NOT NULL DEFAULT 'uk',
    show_both_transcripts INTEGER NOT NULL DEFAULT 0,
    show_summary INTEGER NOT NULL DEFAULT 0
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError(f"Database path must be absolute: {path}")
        self._path = path
        self._conn: aiosqlite.Connection | None = None
        self._retries = settings.sqlite_retry_count
        self._retry_delay = settings.sqlite_retry_base_delay

    async def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._migrate_transcripts_table()
        await self._conn.executescript(_SCHEMA)
        await self._migrate_user_whisper_models()
        await self._conn.commit()
        logger.info("SQLite database ready at %s (WAL mode)", self._path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _migrate_transcripts_table(self) -> None:
        """Drop legacy transcripts table (no auto-increment id) if present."""
        conn = self._require_conn()
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transcripts'"
        ) as cursor:
            if not await cursor.fetchone():
                return
        async with conn.execute("PRAGMA table_info(transcripts)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if "id" not in columns:
            logger.warning("Migrating legacy transcripts table to new schema")
            await conn.execute("DROP TABLE transcripts")

    async def _migrate_user_whisper_models(self) -> None:
        """Upgrade removed whisper model aliases stored in user settings."""
        conn = self._require_conn()
        cursor = await conn.execute(
            "UPDATE user_settings SET whisper_model = 'medium' WHERE whisper_model = 'base'"
        )
        if cursor.rowcount:
            logger.info("Migrated %s user(s) from whisper model 'base' to 'medium'", cursor.rowcount)

    def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def _retry(self, label: str, operation):
        return await with_sqlite_retry(
            operation,
            retries=self._retries,
            base_delay=self._retry_delay,
            label=label,
        )

    async def insert_transcript(
        self,
        chat_id: int,
        voice_message_id: int,
        text: str,
        ttl_seconds: int,
    ) -> int:
        async def _op() -> int:
            now = time.time()
            expires_at = now + ttl_seconds
            conn = self._require_conn()
            async with conn.execute(
                """
                INSERT INTO transcripts (chat_id, voice_message_id, text, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, voice_message_id) DO UPDATE SET
                    text = excluded.text,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                RETURNING id
                """,
                (chat_id, voice_message_id, text, now, expires_at),
            ) as cursor:
                row = await cursor.fetchone()
                await conn.commit()
                if row is None:
                    raise RuntimeError("Failed to insert transcript row")
                return int(row["id"])

        return await self._retry("insert_transcript", _op)

    async def pop_transcript_by_id(self, transcript_id: int, chat_id: int) -> str | None:
        async def _op() -> str | None:
            conn = self._require_conn()
            now = time.time()
            async with conn.execute(
                """
                SELECT text FROM transcripts
                WHERE id = ? AND chat_id = ? AND expires_at > ?
                """,
                (transcript_id, chat_id, now),
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
            await conn.execute(
                "DELETE FROM transcripts WHERE id = ? AND chat_id = ?",
                (transcript_id, chat_id),
            )
            await conn.commit()
            return row["text"]

        return await self._retry("pop_transcript", _op)

    async def cleanup_expired_transcripts(self) -> int:
        async def _op() -> int:
            conn = self._require_conn()
            cursor = await conn.execute(
                "DELETE FROM transcripts WHERE expires_at <= ?",
                (time.time(),),
            )
            await conn.commit()
            return cursor.rowcount

        return await self._retry("cleanup_expired", _op)

    async def is_group_enabled(self, chat_id: int) -> bool:
        async def _op() -> bool:
            conn = self._require_conn()
            async with conn.execute(
                "SELECT enabled FROM group_settings WHERE chat_id = ?",
                (chat_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row["enabled"]) if row else False

        return await self._retry("is_group_enabled", _op)

    async def set_group_enabled(self, chat_id: int, enabled: bool) -> None:
        async def _op() -> None:
            conn = self._require_conn()
            await conn.execute(
                """
                INSERT INTO group_settings (chat_id, enabled) VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET enabled = excluded.enabled
                """,
                (chat_id, int(enabled)),
            )
            await conn.commit()

        await self._retry("set_group_enabled", _op)

    async def load_all_user_settings(self) -> list[dict]:
        async def _op() -> list[dict]:
            conn = self._require_conn()
            async with conn.execute(
                """
                SELECT user_id, whisper_model, llm_model, language, ui_language,
                       show_both_transcripts, show_summary
                FROM user_settings
                """
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

        return await self._retry("load_all_user_settings", _op)

    async def upsert_user_settings(
        self,
        user_id: int,
        *,
        whisper_model: str,
        llm_model: str,
        language: str,
        ui_language: str,
        show_both_transcripts: bool,
        show_summary: bool,
    ) -> None:
        async def _op() -> None:
            conn = self._require_conn()
            await conn.execute(
                """
                INSERT INTO user_settings (
                    user_id, whisper_model, llm_model, language, ui_language,
                    show_both_transcripts, show_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    whisper_model = excluded.whisper_model,
                    llm_model = excluded.llm_model,
                    language = excluded.language,
                    ui_language = excluded.ui_language,
                    show_both_transcripts = excluded.show_both_transcripts,
                    show_summary = excluded.show_summary
                """,
                (
                    user_id,
                    whisper_model,
                    llm_model,
                    language,
                    ui_language,
                    int(show_both_transcripts),
                    int(show_summary),
                ),
            )
            await conn.commit()

        await self._retry("upsert_user_settings", _op)
