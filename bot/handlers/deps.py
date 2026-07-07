"""Shared application dependencies for handlers."""

from __future__ import annotations

from dataclasses import dataclass

from bot.services import LLMService, TaskQueue, TranscriptionService, WhisperService
from bot.storage import SettingsStore, TranscriptCache


@dataclass
class AppContext:
    settings: SettingsStore
    cache: TranscriptCache
    transcription: TranscriptionService
    queue: TaskQueue
    whisper: WhisperService
    llm: LLMService
