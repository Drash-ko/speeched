"""Persistent transcript cache backed by SQLite."""

from __future__ import annotations

import logging

from bot.storage.database import Database

logger = logging.getLogger(__name__)


class TranscriptCache:
    def __init__(self, db: Database, ttl_seconds: int = 3600) -> None:
        self._db = db
        self._ttl = ttl_seconds

    async def set(self, chat_id: int, voice_message_id: int, text: str) -> int:
        row_id = await self._db.insert_transcript(
            chat_id, voice_message_id, text, self._ttl
        )
        logger.debug(
            "Cached transcript id=%s chat=%s voice_msg=%s",
            row_id,
            chat_id,
            voice_message_id,
        )
        return row_id

    async def pop_by_id(self, transcript_id: int, chat_id: int) -> str | None:
        text = await self._db.pop_transcript_by_id(transcript_id, chat_id)
        if text:
            logger.debug("Popped transcript id=%s chat=%s", transcript_id, chat_id)
        return text

    async def cleanup_expired(self) -> int:
        removed = await self._db.cleanup_expired_transcripts()
        if removed:
            logger.debug("Removed %s expired transcript rows", removed)
        return removed
