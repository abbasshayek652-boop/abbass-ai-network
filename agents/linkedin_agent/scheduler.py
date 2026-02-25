from __future__ import annotations

import asyncio
import random
from typing import Any

from .service import LinkedInService, service


class LinkedInScheduler:
    """Background poller publishing scheduled LinkedIn posts."""

    def __init__(self, svc: LinkedInService, interval: int = 60) -> None:
        self._service = svc
        self._interval = interval
        self._task: asyncio.Task[Any] | None = None
        self._running = False

    async def _run(self) -> None:
        while self._running:
            self._service.publish_due()
            delay = self._interval + random.uniform(0, 3)
            await asyncio.sleep(delay)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover - expected
                pass
            self._task = None

    async def run_once(self) -> None:
        self._service.publish_due()


def start_scheduler(app: Any, svc: LinkedInService | None = None) -> LinkedInScheduler:
    scheduler = LinkedInScheduler(svc or service)
    scheduler.start()
    setattr(app.state, "linkedin_scheduler", scheduler)
    return scheduler
