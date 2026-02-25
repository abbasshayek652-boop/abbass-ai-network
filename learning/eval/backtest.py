from __future__ import annotations

from typing import Dict, List

from sqlmodel import Session

from learning.data_schema import PolicyMetric


def run_backtest(dataset: List[Dict[str, float]]) -> Dict[str, float]:
    if not dataset:
        return {"sharpe": 0.0, "max_drawdown": 0.0, "win_rate": 0.0}
    returns = [float(row.get("forward_return", 0.0)) for row in dataset]
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    std = variance ** 0.5
    sharpe = mean_ret / (std + 1e-6) * (252 ** 0.5)
    cumulative: List[float] = []
    running = 0.0
    for value in returns:
        running += value
        cumulative.append(running)
    peak = -float("inf")
    max_dd = 0.0
    for value in cumulative:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_dd:
            max_dd = drawdown
    wins = sum(1 for value in returns if value > 0) / len(returns)
    return {"sharpe": sharpe, "max_drawdown": max_dd, "win_rate": wins}


def persist_metrics(engine, policy_id: int, metrics: Dict[str, float]) -> None:
    with Session(engine) as session:
        for name, value in metrics.items():
            session.add(PolicyMetric(policy_id=policy_id, metric_name=name, metric_value=value))
        session.commit()
