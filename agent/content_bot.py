from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from ai.base_agent import Agent

LOGGER = logging.getLogger(__name__)


class ContentAgent(Agent):
    name = "content"
    description = "Drafts distribution-ready content snippets."

    async def start(self) -> None:
        self.running = True
        self.config.setdefault("published", 0)
        LOGGER.info("Content agent started")

    async def stop(self) -> None:
        self.running = False
        LOGGER.info("Content agent stopped")

    async def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "published": self.config.get("published", 0),
            "last_topic": self.config.get("last_topic"),
        }

    async def on_tick(self) -> None:
        if not self.running:
            return
        topic = self.config.get("default_topic", "Daily insights")
        self.config["last_topic"] = topic
        self.config["published"] = int(self.config.get("published", 0)) + 1
        LOGGER.info("Prepared content piece on %s", topic)
        await asyncio.sleep(0)


__all__ = ["ContentAgent"]

