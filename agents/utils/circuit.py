from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CircuitBreakerConfig:
    max_failures: int = 5
    window_secs: int = 300


@dataclass
class CircuitBreaker:
    config: CircuitBreakerConfig
    _events: Dict[str, list[float]] = field(default_factory=dict)
    tripped: bool = False

    def record(self, key: str) -> None:
        now = time.time()
        entries = self._events.setdefault(key, [])
        entries.append(now)
        self._events[key] = [t for t in entries if now - t <= self.config.window_secs]
        total = sum(len(v) for v in self._events.values())
        if total >= self.config.max_failures:
            self.tripped = True

    def reset(self) -> None:
        self._events.clear()
        self.tripped = False

