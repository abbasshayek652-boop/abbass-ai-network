from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from adapters.exchange.base import ExchangeAdapter
from adapters.exchange.binance import BinanceAdapter
from oms.orders import OrderIntent
from oms.execution import Executor
from telemetry.metrics import router_failover_total

LOGGER = logging.getLogger(__name__)


@dataclass
class VenueState:
    name: str
    adapter: ExchangeAdapter
    rate_limit_per_min: int = 120
    tokens: float = field(default=120.0)
    last_refill: float = field(default_factory=time.monotonic)
    success_latency_ms: float = 0.0
    failures: int = 0
    successes: int = 0

    def healthy(self) -> bool:
        return self.failures < 5 or self.successes > 0

    def acquire(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        refill = (self.rate_limit_per_min / 60.0) * elapsed
        if refill > 0:
            self.tokens = min(self.rate_limit_per_min, self.tokens + refill)
            self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


def _build_adapter(name: str, paper: bool, api_key: Optional[str], api_secret: Optional[str]) -> ExchangeAdapter:
    normalized = name.lower()
    if normalized == "binance":
        return BinanceAdapter(paper=paper, api_key=api_key, api_secret=api_secret)
    # Fallback: reuse Binance adapter for unsupported exchanges in paper mode.
    LOGGER.warning("Exchange %s not implemented, defaulting to Binance paper adapter", name)
    return BinanceAdapter(paper=True, api_key=api_key, api_secret=api_secret)


class ExchangeRouter:
    """Routes requests across multiple exchanges with basic health tracking."""

    def __init__(
        self,
        exchanges: Iterable[str],
        *,
        paper: bool,
        api_key: Optional[str],
        api_secret: Optional[str],
        agent: str = "crypto",
    ) -> None:
        self.venues: Dict[str, VenueState] = {
            name: VenueState(
                name=name,
                adapter=_build_adapter(name, paper, api_key, api_secret),
            )
            for name in exchanges
        }
        self.primary = next(iter(self.venues.values()), None)
        self.agent = agent

    async def init(self) -> None:
        await asyncio.gather(*(venue.adapter.init() for venue in self.venues.values()))

    async def fetch_markets(self) -> Dict[str, Dict[str, Any]]:
        if not self.primary:
            return {}
        return await self.primary.adapter.fetch_markets()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        if not self.primary:
            return []
        return await self.primary.adapter.fetch_ohlcv(symbol, timeframe, limit)

    async def fetch_balance(self) -> Dict[str, Any]:
        if not self.primary:
            return {}
        return await self.primary.adapter.fetch_balance()

    async def best_quote(self, symbol: str, side: str) -> Tuple[str, Dict[str, Any]]:
        candidates: List[Tuple[str, Dict[str, Any], float]] = []
        for name, venue in self.venues.items():
            if not venue.acquire():
                continue
            start = time.monotonic()
            try:
                ticker = await venue.adapter.fetch_ticker(symbol)
            except Exception as exc:  # pragma: no cover - network failure path
                venue.failures += 1
                LOGGER.debug("%s ticker failure: %s", name, exc)
                continue
            latency_ms = (time.monotonic() - start) * 1000
            venue.success_latency_ms = (venue.success_latency_ms + latency_ms) / 2
            venue.successes += 1
            price = float(ticker.get("last") or ticker.get("close") or 0.0)
            if price <= 0:
                continue
            candidates.append((name, ticker, price))
        if not candidates:
            raise RuntimeError("No healthy venues available")
        reverse = side == "sell"
        candidates.sort(key=lambda tup: tup[2], reverse=reverse)
        winner = candidates[0]
        return winner[0], winner[1]

    def health_snapshot(self) -> Dict[str, Dict[str, float]]:
        return {
            name: {
                "latency_ms": venue.success_latency_ms,
                "failures": float(venue.failures),
                "tokens": float(venue.tokens),
            }
            for name, venue in self.venues.items()
        }

    async def execute(
        self,
        intent: OrderIntent,
        executor: Executor,
        *,
        side: Optional[str] = None,
        slippage_bps: int = 0,
    ) -> Tuple[bool, Dict[str, Any], str]:
        side = side or intent.side
        ordered = list(self.venues.keys())
        try:
            best, _ = await self.best_quote(intent.symbol, side)
            ordered.remove(best)
            ordered.insert(0, best)
        except Exception:
            LOGGER.debug("Unable to determine best quote; falling back to order of venues")
        attempts: List[Tuple[str, Exception]] = []
        for name in ordered:
            venue = self.venues[name]
            if not venue.acquire():
                continue
            try:
                success, payload = await executor.execute(
                    intent,
                    adapter=venue.adapter,
                    slippage_bps=slippage_bps,
                )
                if success:
                    venue.successes += 1
                    return success, payload, name
            except Exception as exc:  # pragma: no cover - runtime failure
                venue.failures += 1
                attempts.append((name, exc))
                continue
        if attempts:
            for idx in range(len(attempts) - 1):
                current, nxt = attempts[idx], attempts[idx + 1]
                router_failover_total.labels(self.agent, current[0], nxt[0]).inc()
        raise RuntimeError("All venues failed to execute order")


async def gather_quotes(router: ExchangeRouter, symbol: str, side: str) -> Tuple[str, Dict[str, Any]]:
    return await router.best_quote(symbol, side)

