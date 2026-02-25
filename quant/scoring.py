from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class Score:
    symbol: str
    value: float
    signal: str  # "buy" | "sell" | "hold"


def normalize(values: Sequence[float]) -> List[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(val - lo) / (hi - lo) for val in values]


def signal_strength(momentum: float, vol: float, news: float, weights: tuple[float, float, float] = (0.5, 0.3, 0.2)) -> float:
    return momentum * weights[0] + (1 - vol) * weights[1] + news * weights[2]


def to_signal(value: float, thresholds: tuple[float, float] = (0.65, 0.35)) -> str:
    if value >= thresholds[0]:
        return "buy"
    if value <= thresholds[1]:
        return "sell"
    return "hold"

