import asyncio
import time
from typing import Any, Dict, List

import pytest
from sqlmodel import Session, select

from agents.crypto_agent import CryptoTradingAgent
from persistence.db import Trade


class FakeAdapter:
    def __init__(self) -> None:
        self.price = 100.0
        self._markets = {
            "BTC/USDT": {
                "limits": {"cost": {"min": 5}},
                "stepSize": 0.001,
                "precision": {"amount": 6},
            }
        }
        now = time.time()
        self._ohlcv = [
            [now - i * 60, 100.0, 100.0, 100.0, 100.0, 1.0]
            for i in range(120, 0, -1)
        ]

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return {"symbol": symbol, "last": self.price}

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        return self._ohlcv[-limit:]

    async def fetch_balance(self) -> Dict[str, Any]:
        return {"free": {"USDT": 1000.0}, "total": {}}

    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: float | None = None,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {"filled": amount, "price": self.price, "fee": 0.0, "orderId": "live"}


class FakeRouter:
    def __init__(
        self,
        exchanges,
        *,
        paper: bool,
        api_key: str | None,
        api_secret: str | None,
        agent: str = "crypto",
    ) -> None:
        self.adapter = FakeAdapter()
        self.paper = paper
        self.executions: List[Any] = []

    async def init(self) -> None:
        return None

    async def fetch_markets(self) -> Dict[str, Dict[str, Any]]:
        return self.adapter._markets

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        return await self.adapter.fetch_ohlcv(symbol, timeframe, limit)

    async def fetch_balance(self) -> Dict[str, Any]:
        return await self.adapter.fetch_balance()

    async def best_quote(self, symbol: str, side: str):
        return "fake", {"last": self.adapter.price}

    async def execute(self, intent, executor, *, side: str | None = None, slippage_bps: int = 0):
        self.executions.append(intent)
        return True, {"filled": intent.qty, "price": self.adapter.price, "fee": 0.0, "orderId": "paper"}, "fake"

    def health_snapshot(self) -> Dict[str, Dict[str, float]]:
        return {"fake": {"latency_ms": 10.0, "failures": 0.0, "tokens": 100.0}}

    @property
    def primary(self):
        class _Primary:
            def __init__(self, adapter) -> None:
                self.adapter = adapter

        return _Primary(self.adapter)


class TestStrategy:
    name = "test"

    async def compute_features(self, ohlcv: List[List[float]]) -> Dict[str, float]:
        return {"momentum": 0.8, "volatility": 0.1, "news": 0.5}

    async def signal(self, features: Dict[str, float]) -> Dict[str, Any]:
        return {"score": 0.9, "signal": "buy"}


def test_agent_places_order(monkeypatch, tmp_path):
    monkeypatch.setattr("agents.crypto_agent.ExchangeRouter", FakeRouter)
    monkeypatch.setattr(CryptoTradingAgent, "_load_strategy", lambda self, _: TestStrategy())

    agent = CryptoTradingAgent(
        {
            "paper": True,
            "allowed_pairs": ["BTC/USDT"],
            "starting_cash": 15.0,
            "db_url": f"sqlite:///{tmp_path}/trades.db",
            "mode": "live",
            "resume": False,
        }
    )

    async def _run() -> None:
        await agent.start()
        await agent.on_tick()
        status = await agent.status()
        assert status["open_positions"]["BTC/USDT"]["qty"] > 0
        assert status["last_scores"]["BTC/USDT"] == pytest.approx(0.9)
        with Session(agent.db_engine) as session:
            trades = session.exec(select(Trade)).all()
        assert len(trades) == 1
        await agent.stop()

    asyncio.run(_run())

