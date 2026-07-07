"""faster-whisper transcription service."""

from __future__ import annotations

import asyncio
import logging
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

from bot.config import (
    ALLOWED_WHISPER_LANGUAGES,
    AUTO_LANGUAGE_FALLBACK,
    WHISPER_INITIAL_PROMPTS,
    settings,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WhisperResult:
    text: str
    detected_language: str


class WhisperService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._models: dict[str, WhisperModel] = {}
        settings.whisper_cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_model(self, model_name: str) -> WhisperModel:
        logger.info(
            "Loading Whisper model '%s' (device=%s, compute=%s, cache=%s)",
            model_name,
            settings.whisper_device,
            settings.whisper_compute_type,
            settings.whisper_cache_dir,
        )
        return WhisperModel(
            model_name,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            download_root=str(settings.whisper_cache_dir),
        )

    async def _get_model(self, model_name: str) -> WhisperModel:
        async with self._lock:
            if model_name not in self._models:
                self._models[model_name] = await asyncio.to_thread(
                    self._load_model, model_name
                )
            return self._models[model_name]

    async def preload(self, model_name: str) -> None:
        """Warm up model in background to avoid delay on first voice message."""
        await self._get_model(model_name)

    def _detect_allowed_language(self, model: WhisperModel, audio_path: str) -> str:
        """Pick the best language among en/uk/ru only (ignores other languages)."""
        audio = decode_audio(audio_path, sampling_rate=16000)
        detection = model.detect_language(audio)
        if len(detection) == 3:
            detected, _probability, all_probs = detection
        else:
            detected, _probability = detection
            all_probs = []

        if detected in ALLOWED_WHISPER_LANGUAGES:
            logger.info("Auto language detected: %s", detected)
            return detected

        allowed_probs = [
            (lang, prob) for lang, prob in all_probs if lang in ALLOWED_WHISPER_LANGUAGES
        ]
        if allowed_probs:
            best = max(allowed_probs, key=lambda item: item[1])[0]
            logger.info(
                "Auto language restricted to en/uk/ru: %s (Whisper guessed %s)",
                best,
                detected,
            )
            return best

        logger.warning(
            "Could not detect en/uk/ru, falling back to %s",
            AUTO_LANGUAGE_FALLBACK,
        )
        return AUTO_LANGUAGE_FALLBACK

    def _resolve_language(
        self, model: WhisperModel, audio_path: str, language: str | None
    ) -> str:
        if language and language != "auto" and language in ALLOWED_WHISPER_LANGUAGES:
            return language
        return self._detect_allowed_language(model, audio_path)

    def _transcribe_sync(
        self,
        model: WhisperModel,
        audio_path: str,
        language: str | None,
        on_segment: Callable[[int], None] | None,
    ) -> WhisperResult:
        resolved = self._resolve_language(model, audio_path, language)

        transcribe_kwargs: dict = {
            "language": resolved,
            "beam_size": 3,
            "vad_filter": True,
            "condition_on_previous_text": True,
            "compression_ratio_threshold": 2.4,
            "log_prob_threshold": -1.0,
            "no_speech_threshold": 0.6,
        }
        prompt = WHISPER_INITIAL_PROMPTS.get(resolved)
        if prompt:
            transcribe_kwargs["initial_prompt"] = prompt

        segments, info = model.transcribe(audio_path, **transcribe_kwargs)
        total_duration = info.duration or 1.0
        parts: list[str] = []
        last_pct = -1

        for segment in segments:
            text = segment.text.strip()
            if text:
                parts.append(text)
            if on_segment and segment.end:
                pct = int(min(100, segment.end / total_duration * 100))
                if pct >= last_pct + 2 or pct >= 98:
                    on_segment(pct)
                    last_pct = pct

        if on_segment:
            on_segment(100)

        raw_text = " ".join(parts).strip()
        text = unicodedata.normalize("NFC", raw_text)

        logger.debug(
            "Transcribed with resolved language %s (requested %s, detected %s)",
            resolved,
            language or "auto",
            info.language,
        )
        return WhisperResult(text=text, detected_language=resolved)

    async def transcribe(
        self,
        audio_path: str,
        model_name: str,
        language: str | None = None,
        on_segment_progress: Callable[[int], None] | None = None,
    ) -> WhisperResult:
        model = await self._get_model(model_name)
        try:
            result = await asyncio.to_thread(
                self._transcribe_sync,
                model,
                audio_path,
                language,
                on_segment_progress,
            )
            logger.info(
                "Whisper transcribed %s chars with model '%s' (language=%s, detected=%s)",
                len(result.text),
                model_name,
                language or "auto",
                result.detected_language,
            )
            return result
        except Exception:
            logger.exception("Whisper transcription failed for model '%s'", model_name)
            raise
