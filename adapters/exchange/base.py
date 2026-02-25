from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class ExchangeAdapter(abc.ABC):
    """Abstract interface for spot exchange interactions."""

    @abc.abstractmethod
    async def init(self) -> None:
        """Initialise the underlying exchange client."""

    @abc.abstractmethod
    async def fetch_markets(self) -> Dict[str, Dict[str, Any]]:
        """Return market metadata keyed by symbol."""

    @abc.abstractmethod
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Return the latest ticker for the provided symbol."""

    @abc.abstractmethod
    async def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> List[List[float]]:
        """Return historical candles for a symbol."""

    @abc.abstractmethod
    async def fetch_balance(self) -> Dict[str, Any]:
        """Return balance payload with free/total funds."""

    @abc.abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Place an order and return the exchange response."""

    @abc.abstractmethod
    async def fetch_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        """Return currently open orders, optionally filtered by symbol."""

    @abc.abstractmethod
    async def cancel_order(
        self, order_id: str, symbol: str | None = None
    ) -> Dict[str, Any]:
        """Cancel an order and return the exchange response."""
