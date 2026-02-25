from __future__ import annotations

from quant.scoring import signal_strength, to_signal


def evaluate(momentum: float, volatility: float, news: float) -> dict[str, float | str]:
    score = signal_strength(momentum, volatility, news)
    return {"score": score, "signal": to_signal(score)}

