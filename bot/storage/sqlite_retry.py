"""Retry helper for transient SQLite lock errors."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import aiosqlite

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _is_retryable(exc: BaseException) -> bool:
    if not isinstance(exc, aiosqlite.OperationalError):
        return False
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


async def with_sqlite_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 0.05,
    label: str = "sqlite",
) -> T:
    last_error: BaseException | None = None
    for attempt in range(retries):
        try:
            return await operation()
        except BaseException as exc:
            if not _is_retryable(exc) or attempt >= retries - 1:
                raise
            last_error = exc
            delay = base_delay * (2**attempt)
            logger.warning(
                "%s busy (attempt %s/%s), retry in %.2fs",
                label,
                attempt + 1,
                retries,
                delay,
            )
            await asyncio.sleep(delay)
    if last_error:
        raise last_error
    raise RuntimeError("SQLite retry exhausted")
