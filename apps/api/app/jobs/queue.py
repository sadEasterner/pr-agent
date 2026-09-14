from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.logging import get_logger
from app.webhooks.schemas import GiteaWebhookEvent

logger = get_logger(__name__)

ProcessFn = Callable[[GiteaWebhookEvent], Awaitable[None]]


class JobQueue:
    """In-process queue that can later be replaced with Redis/ARQ/Celery."""

    def __init__(self, processor: ProcessFn) -> None:
        self._processor = processor
        self._queue: asyncio.Queue[GiteaWebhookEvent] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def enqueue(self, event: GiteaWebhookEvent) -> None:
        await self._queue.put(event)

    async def _run(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._processor(event)
            except Exception:
                logger.exception(
                    "job_failed",
                    repository=event.repository_name,
                    pr_number=event.pr_number,
                    head_sha=event.head_sha,
                )
            finally:
                self._queue.task_done()
