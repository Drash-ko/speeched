"""Startup validation for volumes, caches, and llama.cpp availability."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import httpx

from bot.config import settings

logger = logging.getLogger(__name__)


def verify_whisper_cache() -> None:
    """Ensure the Whisper/Hugging Face cache directory is writable (volume mounted)."""
    cache_dir = settings.whisper_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)

    probe = cache_dir / ".write_probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()

    hf_home = os.environ.get("HF_HOME", "")
    hub_cache = os.environ.get("HUGGINGFACE_HUB_CACHE", "")
    hub_path = Path(hub_cache) if hub_cache else cache_dir / "hub"
    hub_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Whisper cache OK: dir=%s writable, HF_HOME=%s, HUGGINGFACE_HUB_CACHE=%s",
        cache_dir,
        hf_home,
        hub_cache or hub_path,
    )


def verify_database_dir() -> None:
    db_dir = settings.database_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    probe = db_dir / ".write_probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    logger.info("Database directory OK: %s", db_dir)


async def wait_for_llama() -> None:
    """Block until llama.cpp HTTP API responds (startup + cold container)."""
    if settings.llama_mode != "api":
        return

    base = settings.llama_api_url.rstrip("/")
    urls = (f"{base}/health", f"{base}/v1/models")
    retries = settings.llm_startup_retries
    delay = settings.llm_startup_retry_delay

    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=5.0)) as client:
        for attempt in range(1, retries + 1):
            for url in urls:
                try:
                    response = await client.get(url)
                    if response.status_code < 500:
                        logger.info("llama.cpp API ready at %s", settings.llama_api_url)
                        return
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
                    pass
            if attempt < retries:
                logger.warning(
                    "llama.cpp not ready (attempt %s/%s), retry in %ss",
                    attempt,
                    retries,
                    delay,
                )
                await asyncio.sleep(delay)

    logger.warning(
        "llama.cpp API not reachable after %s attempts — bot will start; "
        "requests use per-call HTTP retry",
        retries,
    )
