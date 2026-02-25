from __future__ import annotations

import math
from typing import Any, Dict


def round_step(qty: float, step: float) -> float:
    """Round ``qty`` down to the nearest ``step`` increment."""
    if step <= 0:
        return max(0.0, qty)
    return math.floor(max(0.0, qty) / step) * step


def conform_qty(symbol: str, qty: float, markets: Dict[str, Dict[str, Any]]) -> float:
    """Return a quantity aligned with the exchange step size for ``symbol``."""
    info = markets.get(symbol, {}) if markets else {}
    step = float(info.get("stepSize", 0.000001))
    rounded = round_step(qty, step)
    precision = info.get("precision")
    if isinstance(precision, dict) and "amount" in precision:
        rounded = round(rounded, int(precision["amount"]))
    return rounded


def min_notional(symbol: str, markets: Dict[str, Dict[str, Any]]) -> float:
    info = markets.get(symbol, {}) if markets else {}
    limits = info.get("limits", {}) if isinstance(info, dict) else {}
    cost = limits.get("cost", {}) if isinstance(limits, dict) else {}
    min_val = cost.get("min") if isinstance(cost, dict) else 0.0
    return float(min_val or 0.0)
