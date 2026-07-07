"""Entry point: python -m bot"""

from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

from bot.config import DEFAULT_UI_LANGUAGE, USER_CONFIG_PATH, settings
from bot.i18n import t
from bot.handlers import register_handlers
from bot.handlers.deps import AppContext
from bot.logging_setup import purge_old_logs, setup_logging
from bot.middleware import AppContextMiddleware
from bot.services import LLMService, TaskQueue, TranscriptionService, WhisperService
from bot.startup_checks import verify_database_dir, verify_whisper_cache, wait_for_llama
from bot.storage import Database, SettingsStore, TranscriptCache

logger = logging.getLogger(__name__)

_CACHE_CLEANUP_INTERVAL = 300  # seconds


async def _setup_bot_commands(bot: Bot) -> None:
    lang = settings.default_ui_language or DEFAULT_UI_LANGUAGE
    await bot.set_my_commands(
        [
            BotCommand(command="start", description=t("cmd_start", lang)),
            BotCommand(command="model", description=t("cmd_model", lang)),
            BotCommand(command="language", description=t("cmd_language", lang)),
            BotCommand(command="settings", description=t("cmd_settings", lang)),
            BotCommand(command="help", description=t("cmd_help", lang)),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        [
            BotCommand(command="bot", description=t("cmd_bot", lang)),
            BotCommand(command="recognition", description=t("cmd_recognition", lang)),
            BotCommand(command="help", description=t("cmd_help", lang)),
        ],
        scope=BotCommandScopeAllGroupChats(),
    )


async def _maintenance_loop(cache: TranscriptCache) -> None:
    log_interval_sec = max(3600, settings.log_cleanup_interval_hours * 3600)
    last_log_purge = time.monotonic()

    while True:
        await asyncio.sleep(_CACHE_CLEANUP_INTERVAL)
        await cache.cleanup_expired()

        now = time.monotonic()
        if now - last_log_purge >= log_interval_sec:
            purged = purge_old_logs()
            if purged:
                logger.info("Purged %s rotated log file(s)", purged)
            last_log_purge = now


async def main() -> None:
    settings.apply_runtime_env()
    setup_logging()
    settings.validate()
    verify_whisper_cache()
    verify_database_dir()

    db = Database(settings.database_path)
    await db.connect()

    settings_store = SettingsStore(db)
    await settings_store.load_from_database()
    await settings_store.load_user_config(USER_CONFIG_PATH)

    cache = TranscriptCache(db, ttl_seconds=settings.cache_ttl_seconds)
    whisper = WhisperService()
    llm = LLMService()
    transcription = TranscriptionService(whisper, llm)
    queue = TaskQueue(worker_count=settings.worker_count)

    app = AppContext(
        settings=settings_store,
        cache=cache,
        transcription=transcription,
        queue=queue,
        whisper=whisper,
        llm=llm,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.middleware(AppContextMiddleware(app))
    register_handlers(dp)

    await llm.start()
    await wait_for_llama()
    await queue.start()
    await _setup_bot_commands(bot)
    asyncio.create_task(
        whisper.preload(settings.default_whisper_model),
        name="whisper-preload",
    )
    maintenance_task = asyncio.create_task(_maintenance_loop(cache))

    logger.info(
        "Bot starting (workers=%s, llama_mode=%s, db=%s, hf_home=%s)",
        settings.worker_count,
        settings.llama_mode,
        settings.database_path,
        settings.whisper_cache_dir,
    )

    try:
        await dp.start_polling(bot)
    finally:
        maintenance_task.cancel()
        await queue.stop()
        await llm.stop()
        await db.close()
        await bot.session.close()
        logger.info("Bot stopped")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
