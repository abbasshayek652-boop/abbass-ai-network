from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Cooldown:
    duplicate_secs: int = 20
    loss_cooldown_secs: int = 120


class CooldownState:
    def __init__(self) -> None:
        self._last: dict[tuple[str, str], float] = {}

    def too_soon(self, symbol: str, side: str, cd: Cooldown) -> bool:
        now = time.time()
        key = (symbol, side)
        last = self._last.get(key, 0.0)
        if now - last < cd.duplicate_secs:
            return True
        self._last[key] = now
        return False
