from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Sequence

try:  # pragma: no cover - fallback for offline environments
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - executed when numpy unavailable
    np = None

from analytics.signal_strength import evaluate

PARAM_FILE = Path(__file__).with_name("params").joinpath("momentum_ema.json")


def _load_params(timeframe: str | None = None) -> Dict[str, int]:
    if not PARAM_FILE.exists():
        return {"ema_fast": 12, "ema_slow": 26}
    data = json.loads(PARAM_FILE.read_text())
    if timeframe and timeframe in data:
        return data[timeframe]
    return data.get("default", {"ema_fast": 12, "ema_slow": 26})


class MomentumEMAStrategy:
    name = "momentum_ema"

    def __init__(
        self,
        *,
        ema_fast: int | None = None,
        ema_slow: int | None = None,
        timeframe: str | None = None,
    ) -> None:
        params = _load_params(timeframe)
        self.ema_fast = ema_fast or params.get("ema_fast", 12)
        self.ema_slow = ema_slow or params.get("ema_slow", 26)

    async def compute_features(self, ohlcv: Sequence[Sequence[float]]) -> Dict[str, float]:
        closes = [float(c[4]) for c in ohlcv]
        if np is not None:
            close_arr = np.array(closes, dtype=float)
            ema_fast = close_arr[-self.ema_fast :].mean()
            ema_slow = close_arr[-self.ema_slow :].mean()
            raw_momentum = (ema_fast - ema_slow) / max(1e-8, ema_slow)
            momentum = float(np.clip(raw_momentum, 0.0, 1.0))
            ret = np.diff(close_arr[-21:]) / close_arr[-21:-1]
            vol = float(np.clip(np.std(ret) * np.sqrt(21), 0.0, 1.0))
        else:
            ema_fast = sum(closes[-self.ema_fast :]) / self.ema_fast
            ema_slow = sum(closes[-self.ema_slow :]) / self.ema_slow
            raw_momentum = (ema_fast - ema_slow) / max(1e-8, ema_slow)
            momentum = max(0.0, min(1.0, raw_momentum))
            returns = [
                (closes[i + 1] - closes[i]) / closes[i]
                for i in range(len(closes[-21:]) - 1)
            ]
            mean_ret = sum(returns) / len(returns) if returns else 0.0
            variance = (
                sum((r - mean_ret) ** 2 for r in returns) / len(returns)
                if returns
                else 0.0
            )
            vol = max(0.0, min(1.0, (variance ** 0.5) * (21**0.5)))
        news = 0.5
        return {"momentum": momentum, "volatility": vol, "news": news}

    async def signal(self, features: Dict[str, float]) -> Dict[str, float | str]:
        return evaluate(features["momentum"], features["volatility"], features["news"])
