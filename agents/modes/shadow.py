from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class ShadowStats:
    drawdown_limit: float = 0.1
    error_window_secs: int = 300
    max_errors: int = 3


@dataclass
class ModeState:
    mode: str
    canary_fraction: float
    stats: ShadowStats = field(default_factory=ShadowStats)
    _shadow_trades: list[dict] = field(default_factory=list)
    _errors: list[float] = field(default_factory=list)
    _canary_drawdown: float = 0.0

    def record_shadow(self, payload: dict) -> None:
        self._shadow_trades.append({"ts": time.time(), **payload})

    def split(self, qty: float) -> Tuple[float, float]:
        if self.mode == "shadow":
            return 0.0, qty
        if self.mode == "canary":
            live = qty * max(0.0, min(1.0, self.canary_fraction))
            return live, qty - live
        return qty, 0.0

    def record_error(self) -> None:
        now = time.time()
        self._errors.append(now)
        self._errors = [t for t in self._errors if now - t <= self.stats.error_window_secs]

    def should_halt(self) -> bool:
        if self.mode != "canary":
            return False
        if len(self._errors) >= self.stats.max_errors:
            return True
        if self._canary_drawdown >= self.stats.drawdown_limit:
            return True
        return False

    def update_drawdown(self, start_equity: float, current_equity: float) -> None:
        if start_equity <= 0:
            return
        drawdown = 1 - (current_equity / start_equity)
        if drawdown > self._canary_drawdown:
            self._canary_drawdown = drawdown

    def exports(self) -> Dict[str, float]:
        return {
            "shadow_trades": float(len(self._shadow_trades)),
            "errors": float(len(self._errors)),
            "canary_drawdown": self._canary_drawdown,
        }

