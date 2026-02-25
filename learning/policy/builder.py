from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class PolicyBundle:
    routing_weights: Dict[str, float]
    risk_caps: Dict[str, float]
    strategy_params: Dict[str, float]
    metadata: Dict[str, float | str]

    def as_dict(self) -> Dict[str, object]:
        return {
            "routing": self.routing_weights,
            "risk_caps": self.risk_caps,
            "strategy_params": self.strategy_params,
            "metadata": self.metadata,
        }


def build_policy_bundle(
    *,
    routing: Dict[str, float],
    risk_caps: Dict[str, float],
    strategy_params: Dict[str, float],
    constraints: Dict[str, float],
) -> PolicyBundle:
    max_trade = risk_caps.get("max_notional_per_trade", constraints.get("max_notional_per_trade", 15.0))
    if max_trade > constraints.get("max_notional_per_trade", 15.0):
        risk_caps["max_notional_per_trade"] = constraints["max_notional_per_trade"]
    total = risk_caps.get("max_total_exposure_usdt")
    cap_total = constraints.get("max_total_exposure_usdt")
    if total is not None and cap_total is not None and total > cap_total:
        risk_caps["max_total_exposure_usdt"] = cap_total
    routing_sum = sum(routing.values()) or 1.0
    routing = {k: v / routing_sum for k, v in routing.items()}
    metadata = {"built_ts": 0.0, "source": "learning_engine"}
    return PolicyBundle(routing_weights=routing, risk_caps=risk_caps, strategy_params=strategy_params, metadata=metadata)
