from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass
class DriftAlert:
    triggered: bool
    metric: str
    value: float
    threshold: float


@dataclass
class DriftMonitor:
    baseline: Dict[str, np.ndarray] = field(default_factory=dict)
    thresholds: Dict[str, float] = field(default_factory=lambda: {"psi": 0.25})

    def update_baseline(self, name: str, values: Iterable[float]) -> None:
        arr = [float(v) for v in values]
        if arr:
            self.baseline[name] = arr

    def check(self, name: str, values: Iterable[float]) -> DriftAlert:
        arr = [float(v) for v in values]
        base = self.baseline.get(name)
        if base is None or not len(arr):
            return DriftAlert(False, "psi", 0.0, self.thresholds.get("psi", 0.25))
        combined = arr + base
        lo, hi = min(combined), max(combined)
        if hi == lo:
            return DriftAlert(False, "psi", 0.0, self.thresholds.get("psi", 0.25))
        bucket_size = (hi - lo) / 10
        if bucket_size == 0:
            bucket_size = 1.0
        base_hist: List[float] = [0.0] * 10
        new_hist: List[float] = [0.0] * 10
        for value in base:
            idx = min(9, int((value - lo) / bucket_size))
            base_hist[idx] += 1
        for value in arr:
            idx = min(9, int((value - lo) / bucket_size))
            new_hist[idx] += 1
        base_total = sum(base_hist) or 1.0
        new_total = sum(new_hist) or 1.0
        psi = 0.0
        for b, n in zip(base_hist, new_hist):
            base_prob = b / base_total + 1e-6
            new_prob = n / new_total + 1e-6
            psi += (new_prob - base_prob) * math.log(new_prob / base_prob)
        threshold = self.thresholds.get("psi", 0.25)
        return DriftAlert(psi > threshold, "psi", psi, threshold)
