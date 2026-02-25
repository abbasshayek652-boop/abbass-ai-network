from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable

from risk.rules import RiskCaps


def _kelly_multiplier(volatility: float) -> float:
    if volatility <= 1e-9:
        return 1.0
    scale = max(0.1, min(1.0, 1.0 / (1.0 + volatility * 5)))
    return scale


def dynamic_notional_cap(
    symbol: str,
    volatility: float,
    caps: RiskCaps,
    per_symbol_target: float,
) -> float:
    multiplier = _kelly_multiplier(volatility)
    base_cap = min(per_symbol_target, caps.max_notional_per_trade)
    return base_cap * multiplier


def risk_parity_targets(
    symbols: Iterable[str],
    volatilities: Dict[str, float],
    caps: RiskCaps,
) -> Dict[str, float]:
    symbol_list = list(symbols)
    weights: Dict[str, float] = {}
    for symbol in symbol_list:
        vol = max(volatilities.get(symbol, 0.1), 0.01)
        weights[symbol] = 1.0 / vol
    total_weight = sum(weights.values()) or 1.0
    total_cap = min(caps.max_total_exposure_usdt, caps.max_notional_per_trade * len(symbol_list))
    return {symbol: total_cap * (weight / total_weight) for symbol, weight in weights.items()}


@dataclass
class TrailingStopTracker:
    percent: float
    highs: Dict[str, float] = field(default_factory=dict)

    def update(self, symbol: str, price: float, has_position: bool) -> bool:
        if not has_position or self.percent <= 0:
            self.highs.pop(symbol, None)
            return False
        high = self.highs.get(symbol, price)
        if price > high:
            self.highs[symbol] = price
            return False
        trigger = price <= high * (1 - self.percent)
        if trigger:
            self.highs[symbol] = price
        return trigger

