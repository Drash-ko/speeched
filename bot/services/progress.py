"""Progress reporting via a reply message that becomes the transcription."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.i18n import normalize_ui_language, t

logger = logging.getLogger(__name__)

Stage = Literal["download", "whisper", "llm", "summary", "queue"]


def progress_bar(percent: int, width: int = 12) -> str:
    percent = max(0, min(100, percent))
    filled = round(width * percent / 100)
    return "▪" * filled + "▫" * (width - filled)


def format_status(percent: int, stage_key: str, ui_lang: str) -> str:
    bar = progress_bar(percent)
    label = t(stage_key, ui_lang)
    return f"<i>{label}</i>\n<code>{bar} {percent}%</code>"


def format_queue_status(position: int, ui_lang: str) -> str:
    label = t("stage_queued", ui_lang, position=position)
    return f"<i>{label}</i>"


@dataclass
class ProgressReporter:
    """Edits a reply message: progress bar first, then final transcription."""

    bot: Bot
    chat_id: int
    message_id: int
    ui_lang: str
    _last_text: str = field(default="", init=False)
    _last_percent: int = field(default=-1, init=False)
    _last_stage_key: str = field(default="", init=False)
    _queued: bool = field(default=False, init=False)

    @classmethod
    async def create_reply(
        cls, bot: Bot, voice_message: Message, ui_lang: str
    ) -> ProgressReporter:
        lang = normalize_ui_language(ui_lang)
        reporter = cls(
            bot=bot,
            chat_id=0,
            message_id=0,
            ui_lang=lang,
        )
        text = format_status(0, "stage_download", lang)
        reply = await voice_message.reply(text)
        reporter.chat_id = reply.chat.id
        reporter.message_id = reply.message_id
        reporter._last_text = text
        reporter._last_percent = 0
        return reporter

    async def set_queue_position(self, position: int) -> None:
        if position <= 0:
            return
        self._queued = True
        text = format_queue_status(position, self.ui_lang)
        if text == self._last_text:
            return
        if await self._edit(text):
            self._last_text = text

    async def begin_processing(self) -> None:
        if not self._queued:
            return
        self._queued = False
        self._last_percent = -1
        await self.set_percent(0, "stage_download")

    async def set_percent(self, percent: int, stage_key: str) -> None:
        if self._queued:
            return
        percent = max(0, min(100, percent))
        if percent < self._last_percent:
            return
        if percent == self._last_percent and stage_key == self._last_stage_key:
            return
        if (
            percent - self._last_percent < 1
            and stage_key == self._last_stage_key
            and self._last_percent >= 0
        ):
            return

        text = format_status(percent, stage_key, self.ui_lang)
        if text == self._last_text:
            return

        if await self._edit(text):
            self._last_text = text
            self._last_percent = percent
            self._last_stage_key = stage_key

    async def set_transcription(self, text: str) -> None:
        self._queued = False
        await self._edit(text, clear_markup=True)

    async def set_show_transcription_button(self, callback_data: str) -> None:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t("show_transcription", self.ui_lang),
                        callback_data=callback_data,
                    )
                ]
            ]
        )
        self._queued = False
        try:
            await self.bot.edit_message_text(
                t("transcription_ready", self.ui_lang),
                chat_id=self.chat_id,
                message_id=self.message_id,
                reply_markup=keyboard,
            )
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                logger.debug("Button update skipped: %s", exc)

    async def set_error(self, error_text: str) -> None:
        self._queued = False
        await self._edit(error_text, clear_markup=True)

    async def _edit(self, text: str, *, clear_markup: bool = False) -> bool:
        try:
            kwargs: dict = {
                "chat_id": self.chat_id,
                "message_id": self.message_id,
            }
            if clear_markup:
                kwargs["reply_markup"] = None
            await self.bot.edit_message_text(text, **kwargs)
            return True
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                logger.debug("Message edit skipped: %s", exc)
            return False
