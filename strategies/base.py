from __future__ import annotations

from typing import Any, Dict, Protocol, Sequence


class Strategy(Protocol):
    name: str

    async def compute_features(self, ohlcv: Sequence[Sequence[float]]) -> Dict[str, float]:
        ...

    async def signal(self, features: Dict[str, float]) -> Dict[str, Any]:
        ...
