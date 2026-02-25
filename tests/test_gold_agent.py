import asyncio
from typing import Any, Dict, List

import pytest
from sqlmodel import Session, select

from adapters.exchange.base import ExchangeAdapter
from agents.gold_agent import GoldTradingAgent
from ai.settings import settings
from persistence.db import Trade


class TestStrategy:
    name = "test"

    async def compute_features(self, ohlcv: List[List[float]]) -> Dict[str, float]:
        return {"momentum": 0.9, "volatility": 0.1, "news": 0.5}

    async def signal(self, features: Dict[str, float]) -> Dict[str, Any]:
        return {"score": 0.9, "signal": "buy"}


def _ohlcv_series(price: float) -> List[List[float]]:
    return [[float(idx), price, price, price, price, 1.0] for idx in range(1, 201)]


class FakeAdapter(ExchangeAdapter):
    def __init__(self, price: float = 1900.0) -> None:
        self.price = price
        self._markets = {
            "PAXG/USDT": {
                "limits": {"cost": {"min": 5.0}},
                "stepSize": 0.001,
                "precision": {"amount": 6},
            }
        }
        self._ohlcv = _ohlcv_series(price)

    async def init(self) -> None:  # pragma: no cover - interface requirement
        return None

    async def fetch_markets(self) -> Dict[str, Dict[str, Any]]:
        return self._markets

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return {"symbol": symbol, "last": self.price}

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        return self._ohlcv[-limit:]

    async def fetch_balance(self) -> Dict[str, Any]:
        return {"free": {"USDT": 1_000.0}, "total": {}}

    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: float | None = None,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {"filled": amount, "price": self.price, "fee": 0.0, "orderId": f"paper-{side}"}

    async def fetch_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        return []

    async def cancel_order(self, order_id: str, symbol: str | None = None) -> Dict[str, Any]:
        return {}


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
        self.agent = agent

    async def init(self) -> None:
        return None

    async def fetch_markets(self) -> Dict[str, Dict[str, Any]]:
        return await self.adapter.fetch_markets()

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
            def __init__(self, adapter: FakeAdapter) -> None:
                self.adapter = adapter

        return _Primary(self.adapter)


def _configure_agent(monkeypatch, tmp_path, config: Dict[str, Any]) -> GoldTradingAgent:
    monkeypatch.setattr("agents.crypto_agent.ExchangeRouter", FakeRouter)
    monkeypatch.setattr(GoldTradingAgent, "_load_strategy", lambda self, _: TestStrategy())
    cfg = {
        "paper": True,
        "allowed_pairs": ["PAXG/USDT"],
        "starting_cash": 50.0,
        "db_url": f"sqlite:///{tmp_path}/gold.db",
        "resume": False,
        "mode": "live",
    }
    cfg.update(config)
    return GoldTradingAgent(cfg)


def test_gold_agent_places_capped_order(monkeypatch, tmp_path):
    agent = _configure_agent(monkeypatch, tmp_path, {})

    async def _run() -> None:
        await agent.start()
        await agent.on_tick()
        assert agent.router is not None
        assert len(agent.router.executions) == 1
        intent = agent.router.executions[0]
        price = agent.router.adapter.price
        notional = intent.qty * price
        assert notional <= 15.0 + 1e-6
        assert notional >= 5.0
        step = agent.router.adapter._markets["PAXG/USDT"]["stepSize"]
        ratio = intent.qty / step
        assert ratio == pytest.approx(round(ratio), abs=1e-9)
        with Session(agent.db_engine) as session:
            trades = session.exec(select(Trade)).all()
        assert len(trades) == 1
        await agent.stop()

    asyncio.run(_run())


class FailingAdapter(ExchangeAdapter):
    def __init__(self, *, price: float, fail: bool) -> None:
        self.price = price
        self.fail = fail
        self.orders: List[float] = []
        self._markets = {
            "PAXG/USDT": {
                "limits": {"cost": {"min": 5.0}},
                "stepSize": 0.001,
                "precision": {"amount": 6},
            }
        }
        self._ohlcv = _ohlcv_series(price)

    async def init(self) -> None:
        return None

    async def fetch_markets(self) -> Dict[str, Dict[str, Any]]:
        return self._markets

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return {"symbol": symbol, "last": self.price}

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        return self._ohlcv[-limit:]

    async def fetch_balance(self) -> Dict[str, Any]:
        return {"free": {"USDT": 1_000.0}, "total": {}}

    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: float | None = None,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if self.fail:
            raise RuntimeError("rate limit")
        self.orders.append(amount)
        return {"filled": amount, "price": self.price, "fee": 0.0, "orderId": f"live-{side}"}

    async def fetch_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        return []

    async def cancel_order(self, order_id: str, symbol: str | None = None) -> Dict[str, Any]:
        return {}


def test_gold_router_failover(monkeypatch, tmp_path):
    adapters = {
        "binance": FailingAdapter(price=1895.0, fail=True),
        "okx": FailingAdapter(price=1898.0, fail=False),
    }

    def fake_build(name, paper, api_key, api_secret):
        return adapters[name]

    monkeypatch.setattr("adapters.exchange.router._build_adapter", fake_build)
    monkeypatch.setattr(GoldTradingAgent, "_load_strategy", lambda self, _: TestStrategy())
    monkeypatch.setattr(settings, "binance_key", "key")
    monkeypatch.setattr(settings, "binance_secret", "secret")

    agent = GoldTradingAgent(
        {
            "paper": False,
            "mode": "live",
            "allowed_pairs": ["PAXG/USDT"],
            "starting_cash": 50.0,
            "db_url": f"sqlite:///{tmp_path}/gold_failover.db",
            "resume": False,
            "bypass_canary": True,
            "dry_run_passed": True,
            "confirm_live": "I UNDERSTAND",
            "router_exchanges": ["binance", "okx"],
        }
    )

    async def _run() -> None:
        await agent.start()
        await agent.on_tick()
        assert adapters["binance"].orders == []
        assert len(adapters["okx"].orders) == 1
        executed = adapters["okx"].orders[0]
        assert executed * adapters["okx"].price <= 15.0 + 1e-6
        await agent.stop()

    asyncio.run(_run())


def test_gold_modes_shadow_canary_and_live_checklist(monkeypatch, tmp_path):
    # Shadow mode should avoid live executions.
    shadow_agent = _configure_agent(monkeypatch, tmp_path, {"mode": "shadow"})

    async def _shadow() -> None:
        await shadow_agent.start()
        await shadow_agent.on_tick()
        assert shadow_agent.router is not None
        assert shadow_agent.router.executions == []
        assert len(shadow_agent.mode_state._shadow_trades) == 1
        await shadow_agent.stop()

    asyncio.run(_shadow())

    # Canary mode splits quantity between live and shadow.
    canary_agent = _configure_agent(
        monkeypatch,
        tmp_path,
        {"mode": "canary", "canary_live_fraction": 0.2},
    )

    async def _canary() -> None:
        await canary_agent.start()
        await canary_agent.on_tick()
        assert canary_agent.router is not None
        assert len(canary_agent.router.executions) == 1
        shadow_record = canary_agent.mode_state._shadow_trades[0]
        live_qty = canary_agent.router.executions[0].qty
        total = live_qty + shadow_record["qty"]
        assert total > 0
        assert live_qty / total == pytest.approx(0.2, rel=1e-2)
        await canary_agent.stop()

    asyncio.run(_canary())

    # Live mode requires checklist confirmation.
    monkeypatch.setattr(settings, "binance_key", "key")
    monkeypatch.setattr(settings, "binance_secret", "secret")
    live_agent = _configure_agent(
        monkeypatch,
        tmp_path,
        {
            "paper": False,
            "mode": "live",
            "dry_run_passed": True,
            "bypass_canary": True,
        },
    )

    async def _live_start() -> None:
        await live_agent.start()

    with pytest.raises(RuntimeError):
        asyncio.run(_live_start())


def test_gold_snapshot_resume(monkeypatch, tmp_path):
    base_cfg = {
        "resume": True,
        "snapshot_every": 1,
        "db_url": f"sqlite:///{tmp_path}/gold_snap.db",
    }
    first_agent = _configure_agent(monkeypatch, tmp_path, base_cfg)

    async def _first() -> Dict[str, Any]:
        await first_agent.start()
        await first_agent.on_tick()
        assert first_agent.portfolio is not None
        assert first_agent.portfolio.positions
        await first_agent.stop()
        return {"cash": first_agent.portfolio.cash_usdt, "positions": dict(first_agent.portfolio.positions)}

    first_state = asyncio.run(_first())

    second_agent = _configure_agent(monkeypatch, tmp_path, base_cfg)

    async def _second() -> None:
        await second_agent.start()
        assert second_agent.portfolio is not None
        assert second_agent.portfolio.positions
        for symbol, position in second_agent.portfolio.positions.items():
            assert symbol in first_state["positions"]
        await second_agent.stop()

    asyncio.run(_second())
