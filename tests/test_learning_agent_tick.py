from __future__ import annotations

import asyncio
import time

from ai.learning_engine import LearningEngine
from learning.data_schema import ensure_engine
from learning.ingest import add_event, add_market_snapshot, add_trade, list_advice


def test_learning_engine_tick_and_snapshot() -> None:
    db_url = f"sqlite:///learning_agent_{time.time()}"
    config = {
        "db_url": db_url,
        "redis_url": None,
        "symbols": ["BTC/USDT"],
        "policy_max_caps": {"max_notional_per_trade": 15.0, "max_total_exposure_usdt": 150.0},
    }
    engine = ensure_engine(db_url)
    for idx in range(8):
        add_market_snapshot(engine, symbol="BTC/USDT", price=100 + idx, volume=12 + idx, features={})
        add_trade(
            engine,
            agent="crypto",
            symbol="BTC/USDT",
            side="buy",
            qty=0.1,
            price=100 + idx,
            pnl=0.5,
            paper=True,
        )
    add_event(
        engine,
        agent="gateway",
        kind="market_snapshot",
        payload={"symbol": "BTC/USDT", "features": {"rolling_return": 0.02, "rolling_vol": 0.1}},
    )
    async def _run() -> None:
        agent = LearningEngine(config)
        await agent.start()
        await agent.on_tick()
        status = await agent.status()
        assert status["running"]
        assert "BTC/USDT" in status["last_scores"]
        advice_rows = list_advice(engine, agent="learning")
        assert advice_rows, "Advice rows should be persisted"
        await agent.stop()

        resumed = LearningEngine(config)
        await resumed.start()
        assert resumed.last_scores, "Snapshot should restore scores"

    asyncio.run(_run())
