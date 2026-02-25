from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Dict

from ai.base_agent import Agent

LOGGER = logging.getLogger(__name__)


class Supervisor:
    """Coordinates agent lifecycle and tick scheduling."""

    def __init__(self, agents: Dict[str, Agent]) -> None:
        self.agents = agents
        self.tasks: Dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def start(self, key: str) -> None:
        async with self._lock:
            if key in self.tasks:
                LOGGER.info("Agent %s already started", key)
                return
            agent = self.agents[key]
            if agent.running:
                LOGGER.info("Agent %s already running", key)
                return
            LOGGER.info("Starting agent %s", key)
            await agent.start()
            self.tasks[key] = asyncio.create_task(self._tick_loop(key, agent))

    async def stop(self, key: str) -> None:
        async with self._lock:
            LOGGER.info("Stopping agent %s", key)
            task = self.tasks.pop(key, None)
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            await self.agents[key].stop()

    async def stop_all(self) -> None:
        LOGGER.info("Stopping all agents")
        async with self._lock:
            keys = list(self.tasks.keys())
        await asyncio.gather(*(self.stop(k) for k in keys), return_exceptions=True)

    async def _tick_loop(self, key: str, agent: Agent) -> None:
        interval = max(1, int(agent.config.get("tick_seconds", 5)))
        LOGGER.info("Starting tick loop for %s with interval %s", key, interval)
        try:
            while True:
                if agent.running:
                    await agent.on_tick()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            LOGGER.info("Tick loop for %s cancelled", key)
            raise
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Unhandled error in tick loop for %s", key)
        finally:
            agent.running = False
            LOGGER.info("Tick loop for %s exited", key)

