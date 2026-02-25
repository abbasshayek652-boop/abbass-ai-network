from __future__ import annotations

import asyncio
from typing import Dict

from learning.eval.backtest import persist_metrics, run_backtest
from learning.features.offline import build_offline_dataset
from learning.hpo.optuna_runner import run_hpo
from learning.models.supervised import train_classifier
from learning.policy.builder import build_policy_bundle
from learning.policy.registry import create_policy


async def run_nightly(engine, *, symbol: str, constraints: Dict[str, float]) -> Dict[str, object]:
    dataset = build_offline_dataset(engine, symbol)
    if not dataset:
        return {"created": False, "reason": "no_data"}
    result = train_classifier(dataset, "label")
    hpo_params, score = run_hpo(dataset, "label", {"window": [3, 5, 7]})
    routing = {"binance": 0.5, "okx": 0.5}
    risk_caps = {
        "max_notional_per_trade": min(constraints.get("max_notional_per_trade", 15.0), 15.0),
        "max_total_exposure_usdt": constraints.get("max_total_exposure_usdt", 150.0),
    }
    bundle = build_policy_bundle(routing=routing, risk_caps=risk_caps, strategy_params={"window": hpo_params.get("window", 5)}, constraints=constraints)
    policy = create_policy(engine, payload=bundle.as_dict(), stage="shadow", metrics={"accuracy": result.metrics.get("accuracy", 0.0)})
    backtest_metrics = run_backtest(dataset)
    persist_metrics(engine, policy.id or 0, backtest_metrics)
    await asyncio.sleep(0)
    return {"created": True, "policy_id": policy.id, "metrics": backtest_metrics, "model_score": score}
