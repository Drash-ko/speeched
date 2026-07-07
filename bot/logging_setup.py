"""Logging with rotation; old rotated files purged on a timed schedule only."""

from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bot.config import settings

_ACTIVE_LOG_NAME = "bot.log"


def purge_old_logs() -> int:
    """
    Remove rotated log backups older than LOG_RETENTION_DAYS.
    Never touches the active log file (avoids races with RotatingFileHandler).

    Note: RotatingFileHandler keeps the active file open; on some hosts (e.g. Umbrel)
    an open handle may briefly block deletion of rotated files — skipped files are
    retried on the next scheduled cleanup.
    """
    log_dir = settings.log_file.parent
    retention_days = settings.log_retention_days
    if retention_days <= 0 or not log_dir.exists():
        return 0

    cutoff = time.time() - retention_days * 86400
    removed = 0
    for path in log_dir.glob(f"{_ACTIVE_LOG_NAME}*"):
        if path.name == _ACTIVE_LOG_NAME:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            logging.getLogger(__name__).exception("Failed to remove old log %s", path)
    return removed


def setup_logging() -> None:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
