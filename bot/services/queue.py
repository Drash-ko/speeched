"""Async task queue for non-blocking voice processing."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bot.services.progress import ProgressReporter

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    coro_factory: Callable[[], Awaitable[Any]]
    label: str
    progress: ProgressReporter | None = None


class TaskQueue:
    def __init__(self, worker_count: int = 2) -> None:
        self._worker_count = max(1, worker_count)
        self._queue: asyncio.Queue[QueueItem | None] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._running = False
        self._busy = False
        self._waiters: list[ProgressReporter] = []
        self._state_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for i in range(self._worker_count):
            task = asyncio.create_task(self._worker(i), name=f"voice-worker-{i}")
            self._workers.append(task)
        logger.info("Started %s voice processing workers", self._worker_count)

    async def stop(self) -> None:
        if not self._running:
            return
        for _ in self._workers:
            await self._queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._running = False
        logger.info("Stopped voice processing workers")

    async def submit(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        label: str,
        *,
        progress: ProgressReporter | None = None,
    ) -> None:
        async with self._state_lock:
            if progress:
                self._waiters.append(progress)
            await self._refresh_queue_display()
        await self._queue.put(
            QueueItem(coro_factory=coro_factory, label=label, progress=progress)
        )
        logger.debug("Queued task: %s (queue size ~%s)", label, self._queue.qsize())

    async def _refresh_queue_display(self) -> None:
        for index, reporter in enumerate(self._waiters):
            position = index + 1 + (1 if self._busy else 0)
            if self._busy or index > 0:
                await reporter.set_queue_position(position)
            else:
                await reporter.begin_processing()

    async def _worker(self, worker_id: int) -> None:
        while True:
            item = await self._queue.get()
            try:
                if item is None:
                    break
                async with self._state_lock:
                    self._busy = True
                    if item.progress and item.progress in self._waiters:
                        self._waiters.remove(item.progress)
                    await self._refresh_queue_display()

                logger.debug("Worker %s processing: %s", worker_id, item.label)
                if item.progress:
                    await item.progress.begin_processing()
                await item.coro_factory()
            except Exception:
                if item is not None:
                    logger.exception(
                        "Worker %s failed on task: %s", worker_id, item.label
                    )
            finally:
                if item is not None:
                    async with self._state_lock:
                        self._busy = False
                        await self._refresh_queue_display()
                    self._queue.task_done()
