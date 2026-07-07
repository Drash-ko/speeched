"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
TEMP_DIR = PROJECT_ROOT / "tmp"
DATA_DIR = PROJECT_ROOT / "data"
USER_CONFIG_PATH = PROJECT_ROOT / "config" / "users.yaml"

WHISPER_MODELS = ("medium", "large-v3-turbo")
DEFAULT_WHISPER_MODEL = "medium"
# Standard model needs LLM post-processing; best model is accurate enough alone.
WHISPER_MODELS_NEED_LLM = frozenset({"medium"})
# Removed from picker; migrated to medium on load.
DEPRECATED_WHISPER_MODELS = frozenset({"base"})

UI_LANGUAGES = ("uk", "en")
DEFAULT_UI_LANGUAGE = "en"

# Summary length scales with source text (word counts).
SUMMARY_WORD_RATIO = 0.25
SUMMARY_WORD_MIN = 20
SUMMARY_WORD_MAX = 150

ALLOWED_WHISPER_LANGUAGES = frozenset({"en", "uk", "ru"})
RECOGNITION_LANGUAGES = ("auto", "en", "uk", "ru")
DEFAULT_RECOGNITION_LANGUAGE = "auto"
# When auto mode cannot pick en/uk/ru from audio
AUTO_LANGUAGE_FALLBACK = "uk"

# Biases Whisper toward correct vocabulary (incl. colloquial speech)
WHISPER_INITIAL_PROMPTS: dict[str, str] = {
    "en": (
        "English speech. Casual conversation. "
        "Windows, macOS, Linux, server, folder, network, files."
    ),
    "uk": (
        "Українська мова. Звичайна розмовна мова, можливі нецензурні слова. "
        "Windows, macOS, Linux, сервер, провідник, папка, мережа, файли."
    ),
    "ru": (
        "Русский язык. Разговорная речь, возможна ненормативная лексика. "
        "Windows, macOS, Linux, сервер, проводник, папка, сеть, файлы."
    ),
}

# Qwen2.5-3B default (quality/speed balance on CPU); qwen3-4b as fallback
DEFAULT_LLM_MODEL = "qwen2.5-3b"
LLM_MODEL_FALLBACKS: dict[str, list[str]] = {
    "qwen2.5-3b": ["qwen3-4b"],
    "qwen3-4b": ["qwen2.5-3b"],
}

LLM_MODEL_ALIASES: dict[str, str] = {
    "qwen2.5-3b": "Qwen/Qwen2.5-3B-Instruct-GGUF",
    "qwen3-4b": "Qwen/Qwen3-4B-Instruct-GGUF",
}


def resolve_path(raw: str | Path, default: Path) -> Path:
    """Always return an absolute path (critical for Docker volume mounts)."""
    path = Path(raw) if raw else default
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    whisper_device: str = field(default_factory=lambda: os.getenv("WHISPER_DEVICE", "cpu"))
    whisper_compute_type: str = field(
        default_factory=lambda: os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    )
    whisper_cache_dir: Path = field(
        default_factory=lambda: resolve_path(
            os.getenv("WHISPER_CACHE_DIR", ""),
            PROJECT_ROOT / "whisper-cache",
        )
    )
    default_whisper_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_WHISPER_MODEL", DEFAULT_WHISPER_MODEL)
    )
    default_recognition_language: str = field(
        default_factory=lambda: os.getenv(
            "DEFAULT_RECOGNITION_LANGUAGE", DEFAULT_RECOGNITION_LANGUAGE
        )
    )
    default_ui_language: str = field(
        default_factory=lambda: os.getenv("DEFAULT_UI_LANGUAGE", DEFAULT_UI_LANGUAGE)
    )
    default_llm_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_LLM_MODEL", DEFAULT_LLM_MODEL)
    )
    llama_mode: str = field(default_factory=lambda: os.getenv("LLAMA_MODE", "api"))
    llama_api_url: str = field(
        default_factory=lambda: os.getenv("LLAMA_API_URL", "http://127.0.0.1:8080")
    )
    llama_cli_path: str = field(
        default_factory=lambda: os.getenv("LLAMA_CLI_PATH", "llama-cli")
    )
    llama_model_path: str = field(default_factory=lambda: os.getenv("LLAMA_MODEL_PATH", ""))
    llama_ctx_size: int = field(
        default_factory=lambda: int(os.getenv("LLAMA_CTX_SIZE", "4096"))
    )
    llama_threads: int = field(
        default_factory=lambda: int(os.getenv("LLAMA_THREADS", str(os.cpu_count() or 4)))
    )
    database_path: Path = field(
        default_factory=lambda: resolve_path(
            os.getenv("DATABASE_PATH", ""),
            DATA_DIR / "bot.db",
        )
    )
    log_file: Path = field(
        default_factory=lambda: resolve_path(
            os.getenv("LOG_FILE", ""),
            LOG_DIR / "bot.log",
        )
    )
    log_max_bytes: int = field(
        default_factory=lambda: int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
    )
    log_backup_count: int = field(
        default_factory=lambda: int(os.getenv("LOG_BACKUP_COUNT", "3"))
    )
    log_retention_days: int = field(
        default_factory=lambda: int(os.getenv("LOG_RETENTION_DAYS", "7"))
    )
    log_cleanup_interval_hours: int = field(
        default_factory=lambda: int(os.getenv("LOG_CLEANUP_INTERVAL_HOURS", "24"))
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    )
    worker_count: int = field(default_factory=lambda: int(os.getenv("WORKER_COUNT", "1")))
    sqlite_retry_count: int = field(
        default_factory=lambda: int(os.getenv("SQLITE_RETRY_COUNT", "3"))
    )
    sqlite_retry_base_delay: float = field(
        default_factory=lambda: float(os.getenv("SQLITE_RETRY_BASE_DELAY", "0.05"))
    )
    llm_http_retries: int = field(
        default_factory=lambda: int(os.getenv("LLM_HTTP_RETRIES", "3"))
    )
    llm_http_retry_delay: float = field(
        default_factory=lambda: float(os.getenv("LLM_HTTP_RETRY_DELAY", "2.0"))
    )
    llm_startup_retries: int = field(
        default_factory=lambda: int(os.getenv("LLM_STARTUP_RETRIES", "30"))
    )
    llm_startup_retry_delay: float = field(
        default_factory=lambda: float(os.getenv("LLM_STARTUP_RETRY_DELAY", "2.0"))
    )

    def apply_runtime_env(self) -> None:
        """Point Hugging Face / faster-whisper caches at the persistent volume."""
        cache = str(self.whisper_cache_dir)
        os.environ.setdefault("HF_HOME", cache)
        os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(self.whisper_cache_dir / "hub"))

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        if self.default_whisper_model in DEPRECATED_WHISPER_MODELS:
            self.default_whisper_model = DEFAULT_WHISPER_MODEL
        if self.default_whisper_model not in WHISPER_MODELS:
            raise ValueError(
                f"DEFAULT_WHISPER_MODEL must be one of {WHISPER_MODELS}"
            )
        if self.default_recognition_language not in RECOGNITION_LANGUAGES:
            raise ValueError(
                f"DEFAULT_RECOGNITION_LANGUAGE must be one of {RECOGNITION_LANGUAGES}"
            )
        if self.default_ui_language not in UI_LANGUAGES:
            raise ValueError(f"DEFAULT_UI_LANGUAGE must be one of {UI_LANGUAGES}")
        if self.llama_mode not in ("api", "cli"):
            raise ValueError("LLAMA_MODE must be 'api' or 'cli'")
        if self.llama_mode == "cli" and not self.llama_model_path:
            raise ValueError("LLAMA_MODEL_PATH is required when LLAMA_MODE=cli")
        if not self.database_path.is_absolute():
            raise ValueError(f"DATABASE_PATH must be absolute, got: {self.database_path}")


settings = Settings()
