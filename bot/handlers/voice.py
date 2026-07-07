"""Voice message and video note handlers."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from bot.config import DEFAULT_UI_LANGUAGE
from bot.handlers.callbacks import build_show_transcription_callback
from bot.handlers.deps import AppContext
from bot.i18n import format_user_transcription, t
from bot.services.progress import ProgressReporter

logger = logging.getLogger(__name__)
router = Router(name="voice")


@router.message(F.voice | F.video_note)
async def on_audio_message(message: Message, bot: Bot, app: AppContext) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await _handle_private(message, bot, app)
    elif message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await _handle_group(message, bot, app)
    else:
        ui_lang = await _ui_lang(app, message)
        await message.answer(t("error_unsupported_chat", ui_lang))


async def _ui_lang(app: AppContext, message: Message) -> str:
    if message.from_user:
        return await app.settings.get_ui_language(message.from_user.id)
    return DEFAULT_UI_LANGUAGE


async def _handle_private(message: Message, bot: Bot, app: AppContext) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    whisper_model = await app.settings.get_whisper_model(user_id)
    llm_model = await app.settings.get_llm_model(user_id)
    language = await app.settings.get_language(user_id)
    show_summary = await app.settings.get_show_summary(user_id)
    label = f"private:{message.chat.id}:{message.message_id}"

    progress = await ProgressReporter.create_reply(bot, message, ui_lang)

    async def job() -> None:
        try:
            result = await app.transcription.process_voice(
                bot,
                message,
                whisper_model,
                llm_model,
                language=language,
                progress=progress,
                show_summary=show_summary,
            )
            text = result.text
            if text == "(empty)":
                text = t("empty_transcription", ui_lang)
            output = format_user_transcription(
                text=text,
                summary=result.summary,
                warning_keys=result.warning_keys,
                ui_lang=ui_lang,
            )
            await progress.set_transcription(output)
        except Exception:
            logger.exception("Failed to process private audio %s", label)
            await progress.set_error(t("error_transcription", ui_lang))

    await app.queue.submit(job, label=label, progress=progress)


async def _handle_group(message: Message, bot: Bot, app: AppContext) -> None:
    if not message.from_user:
        return

    if not await app.settings.is_group_enabled(message.chat.id):
        return

    user_id = message.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    chat_id = message.chat.id
    source_message_id = message.message_id
    whisper_model = await app.settings.get_whisper_model(user_id)
    llm_model = await app.settings.get_llm_model(user_id)
    language = await app.settings.get_language(user_id)
    show_summary = await app.settings.get_show_summary(user_id)
    label = f"group:{chat_id}:{source_message_id}"

    progress = await ProgressReporter.create_reply(bot, message, ui_lang)

    async def job() -> None:
        try:
            result = await app.transcription.process_voice(
                bot,
                message,
                whisper_model,
                llm_model,
                language=language,
                progress=progress,
                show_summary=show_summary,
            )
            text = result.text
            if text == "(empty)":
                text = t("empty_transcription", ui_lang)
            full_text = format_user_transcription(
                text=text,
                summary=result.summary,
                warning_keys=result.warning_keys,
                ui_lang=ui_lang,
            )
            transcript_id = await app.cache.set(chat_id, source_message_id, full_text)
            logger.info(
                "Group transcript ready id=%s chat=%s source_msg=%s",
                transcript_id,
                chat_id,
                source_message_id,
            )
            await progress.set_show_transcription_button(
                build_show_transcription_callback(transcript_id)
            )
        except Exception:
            logger.exception("Failed to process group audio %s", label)
            await progress.set_error(t("error_transcription", ui_lang))

    await app.queue.submit(job, label=label, progress=progress)
