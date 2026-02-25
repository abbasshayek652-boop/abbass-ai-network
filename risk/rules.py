from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RiskCaps:
    max_notional_per_trade: float = 15.0
    max_positions_per_symbol: int = 1
    max_total_exposure_usdt: float = 150.0
    max_drawdown_pct_session: float = 0.08
    per_symbol_exposure_usdt: float = 50.0


def check_pre_trade(
    symbol: str,
    price: float,
    qty: float,
    caps: RiskCaps,
    exposures: Dict[str, float],
    total_exposure: float,
) -> tuple[bool, str]:
    notional = price * qty
    if notional <= 0:
        return False, "notional<=0"
    if notional > caps.max_notional_per_trade:
        return False, "cap:notional"
    if total_exposure + notional > caps.max_total_exposure_usdt:
        return False, "cap:total_exposure"
    if exposures.get(symbol, 0.0) + notional > caps.per_symbol_exposure_usdt:
        return False, "cap:per_symbol_exposure"
    return True, "ok"
