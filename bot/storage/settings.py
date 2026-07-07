"""User settings (YAML seed + SQLite persistence) and group ON/OFF state."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml

from bot.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_RECOGNITION_LANGUAGE,
    DEFAULT_UI_LANGUAGE,
    DEFAULT_WHISPER_MODEL,
    DEPRECATED_WHISPER_MODELS,
    RECOGNITION_LANGUAGES,
    UI_LANGUAGES,
    WHISPER_MODELS,
)
from bot.storage.database import Database

logger = logging.getLogger(__name__)


def _normalize_whisper_model(model: str | None) -> str | None:
    if not model:
        return None
    if model in DEPRECATED_WHISPER_MODELS:
        logger.info("Migrating deprecated whisper model '%s' to medium", model)
        return DEFAULT_WHISPER_MODEL
    if model in WHISPER_MODELS:
        return model
    return None


class SettingsStore:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._lock = asyncio.Lock()
        self._user_whisper: dict[int, str] = {}
        self._user_llm: dict[int, str] = {}
        self._user_language: dict[int, str] = {}
        self._user_ui_language: dict[int, str] = {}
        self._user_show_both: dict[int, bool] = {}
        self._user_show_summary: dict[int, bool] = {}
        self._sqlite_user_ids: set[int] = set()

    async def load_from_database(self) -> None:
        rows = await self._db.load_all_user_settings()
        migrate_ids: list[int] = []
        async with self._lock:
            for row in rows:
                user_id = int(row["user_id"])
                self._sqlite_user_ids.add(user_id)
                raw_whisper = row.get("whisper_model")
                whisper = _normalize_whisper_model(raw_whisper)
                if whisper:
                    self._user_whisper[user_id] = whisper
                if raw_whisper in DEPRECATED_WHISPER_MODELS:
                    migrate_ids.append(user_id)
                llm = row.get("llm_model")
                if isinstance(llm, str) and llm.strip():
                    self._user_llm[user_id] = llm.strip()
                language = row.get("language")
                if language in RECOGNITION_LANGUAGES:
                    self._user_language[user_id] = language
                ui_language = row.get("ui_language")
                if ui_language in UI_LANGUAGES:
                    self._user_ui_language[user_id] = ui_language
                if "show_both_transcripts" in row:
                    self._user_show_both[user_id] = bool(row["show_both_transcripts"])
                if "show_summary" in row:
                    self._user_show_summary[user_id] = bool(row["show_summary"])
        logger.info("Loaded persisted settings for %s users from SQLite", len(rows))
        for user_id in migrate_ids:
            await self._persist(user_id)
            logger.info("Migrated deprecated whisper model for user %s", user_id)

    async def load_user_config(self, path: Path) -> None:
        """Seed settings from YAML for users not yet in SQLite."""
        if not path.exists():
            logger.info("User config not found at %s, using defaults", path)
            return
        try:
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            logger.exception("Failed to load user config from %s", path)
            return

        users = data.get("users", {})
        seeded = 0
        for user_id_str, cfg in users.items():
            try:
                user_id = int(user_id_str)
            except ValueError:
                logger.warning("Invalid user id in config: %s", user_id_str)
                continue
            if not isinstance(cfg, dict):
                continue
            async with self._lock:
                if user_id in self._sqlite_user_ids:
                    continue
            await self._apply_config(user_id, cfg)
            seeded += 1
        logger.info("Seeded user config for %s users from YAML", seeded)

    async def _apply_config(self, user_id: int, cfg: dict) -> None:
        whisper = _normalize_whisper_model(cfg.get("whisper_model"))
        llm = cfg.get("llm_model")
        llm_model = llm.strip() if isinstance(llm, str) and llm.strip() else DEFAULT_LLM_MODEL
        language = cfg.get("language")
        if language not in RECOGNITION_LANGUAGES:
            language = DEFAULT_RECOGNITION_LANGUAGE
        ui_language = cfg.get("ui_language")
        if ui_language not in UI_LANGUAGES:
            ui_language = DEFAULT_UI_LANGUAGE
        show_both = bool(cfg.get("show_both_transcripts", False))
        show_summary = bool(cfg.get("show_summary", False))
        whisper_model = whisper or DEFAULT_WHISPER_MODEL

        async with self._lock:
            self._user_whisper[user_id] = whisper_model
            self._user_llm[user_id] = llm_model
            self._user_language[user_id] = language
            self._user_ui_language[user_id] = ui_language
            self._user_show_both[user_id] = show_both
            self._user_show_summary[user_id] = show_summary
            self._sqlite_user_ids.add(user_id)
        await self._persist(user_id)

    async def _persist(self, user_id: int) -> None:
        async with self._lock:
            await self._db.upsert_user_settings(
                user_id,
                whisper_model=self._user_whisper.get(user_id, DEFAULT_WHISPER_MODEL),
                llm_model=self._user_llm.get(user_id, DEFAULT_LLM_MODEL),
                language=self._user_language.get(user_id, DEFAULT_RECOGNITION_LANGUAGE),
                ui_language=self._user_ui_language.get(user_id, DEFAULT_UI_LANGUAGE),
                show_both_transcripts=self._user_show_both.get(user_id, False),
                show_summary=self._user_show_summary.get(user_id, False),
            )
            self._sqlite_user_ids.add(user_id)

    async def get_whisper_model(self, user_id: int) -> str:
        async with self._lock:
            return self._user_whisper.get(user_id, DEFAULT_WHISPER_MODEL)

    async def set_whisper_model(self, user_id: int, model: str) -> None:
        if model not in WHISPER_MODELS:
            raise ValueError(f"Unsupported whisper model: {model}")
        async with self._lock:
            self._user_whisper[user_id] = model
        await self._persist(user_id)

    async def get_llm_model(self, user_id: int) -> str:
        async with self._lock:
            return self._user_llm.get(user_id, DEFAULT_LLM_MODEL)

    async def get_language(self, user_id: int) -> str:
        async with self._lock:
            return self._user_language.get(user_id, DEFAULT_RECOGNITION_LANGUAGE)

    async def set_language(self, user_id: int, language: str) -> None:
        if language not in RECOGNITION_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        async with self._lock:
            self._user_language[user_id] = language
        await self._persist(user_id)

    async def get_ui_language(self, user_id: int) -> str:
        async with self._lock:
            return self._user_ui_language.get(user_id, DEFAULT_UI_LANGUAGE)

    async def set_ui_language(self, user_id: int, language: str) -> None:
        if language not in UI_LANGUAGES:
            raise ValueError(f"Unsupported UI language: {language}")
        async with self._lock:
            self._user_ui_language[user_id] = language
        await self._persist(user_id)

    async def get_show_both_transcripts(self, user_id: int) -> bool:
        async with self._lock:
            return self._user_show_both.get(user_id, False)

    async def set_show_both_transcripts(self, user_id: int, enabled: bool) -> None:
        async with self._lock:
            self._user_show_both[user_id] = enabled
        await self._persist(user_id)

    async def get_show_summary(self, user_id: int) -> bool:
        async with self._lock:
            return self._user_show_summary.get(user_id, False)

    async def set_show_summary(self, user_id: int, enabled: bool) -> None:
        async with self._lock:
            self._user_show_summary[user_id] = enabled
        await self._persist(user_id)

    async def is_group_enabled(self, chat_id: int) -> bool:
        return await self._db.is_group_enabled(chat_id)

    async def set_group_enabled(self, chat_id: int, enabled: bool) -> None:
        await self._db.set_group_enabled(chat_id, enabled)
