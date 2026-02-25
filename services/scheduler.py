from __future__ import annotations

import datetime as dt
import logging
from typing import Awaitable, Callable

StatusProvider = Callable[[], Awaitable[dict[str, object]]]
Notifier = Callable[[str, dict[str, object]], Awaitable[None]]


class ControlScheduler:
    def __init__(self, status_provider: StatusProvider, notifier: Notifier) -> None:
        self._status_provider = status_provider
        self._notifier = notifier
        self._scheduler = _DummyScheduler()

    def start(self) -> None:
        self._scheduler.add_job(self._daily_summary)
        self._scheduler.add_job(self._weekly_compaction)
        self._scheduler.add_job(self._self_check)
        self._scheduler.start()

    async def _daily_summary(self) -> None:
        payload = await self._status_provider()
        await self._notifier("daily_summary", payload)

    async def _weekly_compaction(self) -> None:
        payload = {"event": "audit_compaction", "ts": dt.datetime.utcnow().isoformat()}
        await self._notifier("weekly_audit", payload)

    async def _self_check(self) -> None:
        payload = await self._status_provider()
        await self._notifier("self_check", payload)


async def send_telegram_summary(kind: str, payload: dict[str, object]) -> None:
    logging.getLogger("scheduler").info("scheduler event", extra={"kind": kind, "payload": payload})


def build_scheduler(status_provider: StatusProvider, notifier: Notifier | None = None) -> ControlScheduler:
    return ControlScheduler(status_provider, notifier or send_telegram_summary)


class _DummyScheduler:
    def __init__(self) -> None:
        self._jobs: list[Callable[[], Awaitable[None]]] = []

    def add_job(self, func: Callable[[], Awaitable[None]], *args: object, **kwargs: object) -> None:
        self._jobs.append(func)

    def start(self) -> None:  # pragma: no cover
        return None
