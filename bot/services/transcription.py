"""Voice / video-note download, transcription pipeline, and cleanup."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.types import Message

from bot.config import TEMP_DIR, WHISPER_MODELS_NEED_LLM
from bot.services.llm import LLMService
from bot.services.whisper import WhisperService

if TYPE_CHECKING:
    from bot.services.progress import ProgressReporter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ProgressPlan:
    download_end: int
    whisper_start: int
    whisper_end: int
    llm_start: int
    llm_end: int
    summary_start: int
    summary_end: int


def _build_progress_plan(*, use_llm: bool, use_summary: bool) -> _ProgressPlan:
    if use_llm and use_summary:
        return _ProgressPlan(5, 5, 60, 60, 80, 80, 100)
    if use_llm:
        return _ProgressPlan(5, 5, 75, 75, 100, 100, 100)
    if use_summary:
        return _ProgressPlan(5, 5, 80, 80, 80, 80, 100)
    return _ProgressPlan(10, 10, 100, 100, 100, 100, 100)


def _map_sub_percent(start: int, end: int, sub_percent: int) -> int:
    sub = max(0, min(100, sub_percent))
    return start + (end - start) * sub // 100


@dataclass
class TranscriptionResult:
    text: str
    raw_text: str | None = None
    summary: str | None = None
    warning_keys: list[str] = field(default_factory=list)


class TranscriptionService:
    def __init__(self, whisper: WhisperService, llm: LLMService) -> None:
        self._whisper = whisper
        self._llm = llm
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    async def process_voice(
        self,
        bot: Bot,
        message: Message,
        whisper_model: str,
        llm_model: str,
        *,
        language: str | None = None,
        progress: ProgressReporter | None = None,
        show_summary: bool = False,
    ) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        use_llm = whisper_model in WHISPER_MODELS_NEED_LLM
        plan = _build_progress_plan(use_llm=use_llm, use_summary=show_summary)

        if progress:
            await progress.set_percent(0, "stage_download")

        audio_path = await self._download_audio(bot, message)

        if progress:
            await progress.set_percent(plan.download_end, "stage_download")

        try:
            def on_whisper_segment(pct: int) -> None:
                if progress:
                    total = _map_sub_percent(
                        plan.whisper_start, plan.whisper_end, pct
                    )
                    asyncio.run_coroutine_threadsafe(
                        progress.set_percent(total, "stage_whisper"),
                        loop,
                    )

            whisper_result = await self._whisper.transcribe(
                str(audio_path),
                whisper_model,
                language=language,
                on_segment_progress=on_whisper_segment if progress else None,
            )
            raw_text = whisper_result.text
            detected_language = whisper_result.detected_language

            if not raw_text:
                return TranscriptionResult(
                    text="(empty)",
                    raw_text="",
                    warning_keys=["warn_empty"],
                )

            if progress:
                await progress.set_percent(plan.whisper_end, "stage_whisper")

            text = raw_text
            warning_keys: list[str] = []

            if use_llm:
                if progress:
                    await progress.set_percent(plan.llm_start, "stage_llm")
                try:
                    text = await self._llm.refine(
                        raw_text,
                        llm_model,
                        language=language,
                        detected_language=detected_language,
                    )
                    if progress:
                        await progress.set_percent(plan.llm_end, "stage_llm")
                except Exception:
                    logger.exception("LLM refinement failed, using raw Whisper output")
                    text = raw_text
                    warning_keys.append("warn_llm_skipped")

            summary: str | None = None
            if show_summary:
                if progress:
                    await progress.set_percent(plan.summary_start, "stage_summary")
                try:
                    summary = await self._llm.summarize(
                        text,
                        llm_model,
                        language=language,
                        detected_language=detected_language,
                    )
                    if progress:
                        await progress.set_percent(plan.summary_end, "stage_summary")
                except Exception:
                    logger.exception("LLM summary failed, skipping summary")
                    warning_keys.append("warn_summary_skipped")

            return TranscriptionResult(
                text=text,
                raw_text=raw_text if use_llm else None,
                summary=summary,
                warning_keys=warning_keys,
            )
        finally:
            self._cleanup(audio_path)

    async def _download_audio(self, bot: Bot, message: Message) -> Path:
        if message.voice:
            attachment = message.voice
            default_suffix = ".ogg"
        elif message.video_note:
            attachment = message.video_note
            default_suffix = ".mp4"
        else:
            raise ValueError("Message has no voice or video note attachment")

        suffix = default_suffix
        mime = getattr(attachment, "mime_type", None)
        if mime and "/" in mime:
            ext = mime.split("/")[-1].split(";")[0]
            if ext:
                suffix = f".{ext}"

        filename = f"{message.chat.id}_{message.message_id}_{uuid.uuid4().hex}{suffix}"
        audio_path = TEMP_DIR / filename
        await bot.download(attachment, destination=audio_path)
        logger.debug("Downloaded audio to %s", audio_path)
        return audio_path

    @staticmethod
    def _cleanup(audio_path: Path) -> None:
        try:
            if audio_path.exists():
                audio_path.unlink()
                logger.debug("Removed temp file %s", audio_path)
        except OSError:
            logger.exception("Failed to remove temp file %s", audio_path)
