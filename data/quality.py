from __future__ import annotations

import math
from statistics import median
from typing import Iterable, List, Tuple


class QCResult(Tuple[bool, str | None]):
    pass


def _has_nan(values: Iterable[float]) -> bool:
    for val in values:
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return True
    return False


def validate_ohlcv(
    symbol: str,
    ohlcv: List[List[float]],
    *,
    max_gap_pct: float,
) -> tuple[bool, str | None]:
    if len(ohlcv) < 2:
        return False, "insufficient-bars"
    prev_time = None
    for candle in ohlcv:
        if len(candle) < 6:
            return False, "bad-candle"
        ts, _, _, _, close, volume = candle
        if prev_time is not None and ts <= prev_time:
            return False, "time-order"
        if volume <= 0:
            return False, "zero-volume"
        if _has_nan((close, volume)):
            return False, "nan"
        prev_time = ts
    prev_close = ohlcv[-2][4]
    last_close = ohlcv[-1][4]
    if prev_close > 0:
        gap = abs(last_close - prev_close) / prev_close
        if gap > max_gap_pct:
            return False, "gap"
    return True, None


def validate_ticker(
    price: float,
    history: List[float],
    *,
    deviation_sigma: float,
) -> tuple[bool, str | None]:
    if price <= 0:
        return False, "non-positive"
    if not history:
        return True, None
    med = median(history)
    if med <= 0:
        return True, None
    deviation = abs(price - med) / med
    if deviation > deviation_sigma / 100:
        return False, "deviation"
    return True, None


def update_history(history: List[float], price: float, window: int = 50) -> None:
    history.append(price)
    if len(history) > window:
        del history[0 : len(history) - window]

