from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from ai.base_agent import Agent
from analytics.signal_strength import evaluate

LOGGER = logging.getLogger(__name__)


class CryptoAgent(Agent):
    name = "crypto"
    description = "Generates mock trading signals and logs synthetic trades."

    async def start(self) -> None:
        self.running = True
        self.config.setdefault("last_trade", None)
        LOGGER.info("Crypto agent started")

    async def stop(self) -> None:
        self.running = False
        LOGGER.info("Crypto agent stopped")

    async def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "last_trade": self.config.get("last_trade"),
            "signal": self.config.get("last_signal"),
        }

    async def on_tick(self) -> None:
        if not self.running:
            return
        momentum = self.config.get("momentum", 0.6)
        volatility = self.config.get("volatility", 0.3)
        news = self.config.get("news_sentiment", 0.5)
        analysis = evaluate(momentum, volatility, news)
        self.config["last_signal"] = analysis
        self.config["last_trade"] = datetime.now(timezone.utc).isoformat()
        LOGGER.info("Generated trade signal: %s", analysis)
        await asyncio.sleep(0)


__all__ = ["CryptoAgent"]

