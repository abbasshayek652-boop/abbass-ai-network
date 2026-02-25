from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - import guard for offline environments
    import ccxt  # type: ignore
except Exception as exc:  # pragma: no cover
    ccxt = None  # type: ignore
    _CCXT_IMPORT_ERROR = exc
else:  # pragma: no cover - only executed when ccxt imports cleanly
    _CCXT_IMPORT_ERROR = None

from adapters.exchange.base import ExchangeAdapter

LOGGER = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """ccxt-backed adapter for Binance spot trading."""

    def __init__(
        self,
        *,
        paper: bool = True,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.paper = paper
        self.client: Any | None = None
        self._balance: Dict[str, Any] | None = None
        self.api_key = api_key
        self.api_secret = api_secret

    async def init(self) -> None:
        if ccxt is None:
            raise RuntimeError(
                "ccxt is not available; install the dependency to use BinanceAdapter"
            ) from _CCXT_IMPORT_ERROR

        def _build() -> Any:
            opts = {
                "enableRateLimit": True,
            }
            client = ccxt.binance(opts)  # type: ignore[attr-defined]
            key = self.api_key or os.getenv("MOTHER_BINANCE_KEY")
            secret = self.api_secret or os.getenv("MOTHER_BINANCE_SECRET")
            if not self.paper and key and secret:
                client.apiKey = key
                client.secret = secret
            client.options.setdefault("defaultType", "spot")
            try:
                client.set_sandbox_mode(self.paper)
            except AttributeError:  # pragma: no cover - older ccxt
                LOGGER.debug("Sandbox mode not supported by current ccxt build")
            return client

        self.client = await asyncio.to_thread(_build)
        LOGGER.info("Binance adapter initialised in %s mode", "paper" if self.paper else "live")

    async def fetch_markets(self) -> Dict[str, Dict[str, Any]]:
        markets = await asyncio.to_thread(self.client.fetch_markets)  # type: ignore[union-attr]
        return {m["symbol"]: m for m in markets}

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        ticker = await asyncio.to_thread(self.client.fetch_ticker, symbol)  # type: ignore[union-attr]
        return ticker

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> List[List[float]]:
        return await asyncio.to_thread(
            self.client.fetch_ohlcv, symbol, timeframe, limit  # type: ignore[union-attr]
        )

    async def fetch_balance(self) -> Dict[str, Any]:
        self._balance = await asyncio.to_thread(self.client.fetch_balance)  # type: ignore[union-attr]
        return self._balance

    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.client.create_order,  # type: ignore[union-attr]
            symbol,
            side,
            type,
            amount,
            price,
            params or {},
        )

    async def fetch_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(
            self.client.fetch_open_orders, symbol  # type: ignore[union-attr]
        )

    async def cancel_order(
        self, order_id: str, symbol: str | None = None
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.client.cancel_order, order_id, symbol  # type: ignore[union-attr]
        )
