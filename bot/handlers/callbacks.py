"""Inline button callback handlers."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery

from bot.handlers.deps import AppContext
from bot.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="callbacks")

SHOW_TRANSCRIPTION_PREFIX = "show_tx:"


def build_show_transcription_callback(transcript_id: int) -> str:
    """Short callback id (fits Telegram 64-byte limit)."""
    return f"{SHOW_TRANSCRIPTION_PREFIX}{transcript_id}"


def parse_show_transcription_callback(data: str) -> int | None:
    payload = data.removeprefix(SHOW_TRANSCRIPTION_PREFIX)
    try:
        return int(payload)
    except ValueError:
        return None


@router.callback_query(F.data.startswith(SHOW_TRANSCRIPTION_PREFIX))
async def on_show_transcription(callback: CallbackQuery, app: AppContext) -> None:
    if not callback.message:
        await callback.answer()
        return

    message = callback.message
    ui_lang = await app.settings.get_ui_language(callback.from_user.id)

    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.answer(t("button_groups_only", ui_lang), show_alert=True)
        return

    transcript_id = parse_show_transcription_callback(callback.data or "")
    if transcript_id is None:
        await callback.answer(t("unknown_option", ui_lang), show_alert=True)
        return

    chat_id = message.chat.id
    text = await app.cache.pop_by_id(transcript_id, chat_id)

    if not text:
        await callback.answer(t("transcript_expired", ui_lang), show_alert=True)
        return

    await callback.answer()
    try:
        await message.edit_text(text, reply_markup=None)
    except Exception:
        logger.exception(
            "Failed to edit transcript message id=%s chat=%s", transcript_id, chat_id
        )
        await message.answer(text)
    logger.debug("Served transcript id=%s chat=%s", transcript_id, chat_id)
