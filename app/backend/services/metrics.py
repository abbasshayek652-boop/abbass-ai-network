from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass
from time import monotonic
from typing import Deque, List

from schemas import MetricPoint


@dataclass
class MetricState:
    points: Deque[MetricPoint]
    started_at: float


class MetricService:
    def __init__(self, *, max_points: int = 40) -> None:
        self._state = MetricState(points=deque(maxlen=max_points), started_at=monotonic())
        now = 0
        for i in range(max_points):
            cpu = 40 + 15 * math.sin(i / 4)
            mem = 45 + 10 * math.cos(i / 5)
            pnl = 50 + random.uniform(-5, 5)
            self._state.points.append(MetricPoint(t=now, cpu=cpu, mem=mem, pnl=pnl))
            now += 1

    def current(self) -> List[MetricPoint]:
        return list(self._state.points)

    def append_point(self) -> None:
        last_t = self._state.points[-1].t if self._state.points else 0
        new_t = last_t + 1
        cpu = max(0.0, min(100.0, self._state.points[-1].cpu + random.uniform(-3, 3)))
        mem = max(0.0, min(100.0, self._state.points[-1].mem + random.uniform(-2, 2)))
        pnl = max(0.0, self._state.points[-1].pnl + random.uniform(-3, 3))
        self._state.points.append(MetricPoint(t=new_t, cpu=cpu, mem=mem, pnl=pnl))

    @property
    def uptime(self) -> int:
        return int(monotonic() - self._state.started_at)
