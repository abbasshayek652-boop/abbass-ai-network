import asyncio

import pytest

from adapters.exchange.base import ExchangeAdapter
from adapters.exchange.router import ExchangeRouter
from oms.orders import OrderIntent


class StubAdapter(ExchangeAdapter):
    def __init__(self, *, price: float, fail: bool = False) -> None:
        self.price = price
        self.fail = fail

    async def init(self) -> None:  # pragma: no cover
        return None

    async def fetch_markets(self):  # pragma: no cover
        return {}

    async def fetch_ticker(self, symbol: str):
        return {"last": self.price}

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int):  # pragma: no cover
        return []

    async def fetch_balance(self):  # pragma: no cover
        return {}

    async def create_order(self, symbol: str, side: str, type: str, amount: float, price=None, params=None):
        if self.fail:
            raise RuntimeError("rate limit")
        return {"filled": amount, "price": self.price, "fee": 0.0}

    async def fetch_open_orders(self, symbol=None):  # pragma: no cover
        return []

    async def cancel_order(self, order_id: str, symbol: str | None = None):  # pragma: no cover
        return {}


class StubExecutor:
    async def execute(self, intent, *, adapter, slippage_bps: int = 0):
        return True, await adapter.create_order(intent.symbol, intent.side, intent.type, intent.qty)


def test_router_best_quote_and_failover(monkeypatch):
    adapters = {
        "binance": StubAdapter(price=101.0, fail=True),
        "okx": StubAdapter(price=100.0, fail=False),
    }

    def fake_build(name, paper, api_key, api_secret):
        return adapters[name]

    async def _run() -> None:
        monkeypatch.setattr("adapters.exchange.router._build_adapter", fake_build)
        router = ExchangeRouter(["binance", "okx"], paper=True, api_key=None, api_secret=None)
        await router.init()
        intent = OrderIntent(symbol="BTC/USDT", side="buy", type="market", qty=0.1)
        executor = StubExecutor()
        venue, ticker = await router.best_quote("BTC/USDT", "buy")
        assert venue == "okx"
        success, payload, venue = await router.execute(intent, executor)
        assert success is True
        assert venue == "okx"
        assert payload["price"] == pytest.approx(100.0)

    asyncio.run(_run())

