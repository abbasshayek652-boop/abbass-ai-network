from __future__ import annotations

import asyncio
from learning.ingest import add_market_snapshot, add_trade
from learning.policy.registry import create_policy
from services.learning_api import app, state, policy_latest, policy_promote, score, train


async def _prepare_data() -> None:
    engine = state.engine
    for idx in range(12):
        add_market_snapshot(engine, symbol="BTC/USDT", price=100 + idx, volume=10 + idx, features={})
        add_trade(
            engine,
            agent="crypto",
            symbol="BTC/USDT",
            side="buy",
            qty=0.1,
            price=100 + idx,
            pnl=1.0,
            paper=True,
        )


def test_train_and_score() -> None:
    asyncio.run(_prepare_data())
    metrics = asyncio.run(train({"symbol": "BTC/USDT"}))
    assert metrics["metrics"]["accuracy"] >= 0.5
    payload = asyncio.run(
        score(
            {
                "symbol": "BTC/USDT",
                "features": {"price": 120, "volume": 15, "return": 0.01, "rolling_vol": 0.1, "rolling_return": 0.02, "pnl": 0.5},
            }
        )
    )
    assert 0.0 <= payload["probability"] <= 1.0


def test_policy_promote_flow() -> None:
    policy = create_policy(
        state.engine,
        payload={"routing": {"binance": 1.0}, "risk_caps": {"max_notional_per_trade": 15}},
        stage="shadow",
        metrics={"sharpe_min": 1.0, "max_dd_pct": 0.05},
    )
    latest = asyncio.run(policy_latest("shadow"))
    assert latest["version"] == policy.version
    result = asyncio.run(policy_promote({"policy_id": policy.id, "to_stage": "canary", "thresholds": {"sharpe_min": 0.8, "max_dd_pct": 0.1}}))
    assert result["ok"]
