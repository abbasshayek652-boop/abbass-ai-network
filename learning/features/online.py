from __future__ import annotations

import time
from typing import Dict, Optional

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover - fallback to in-memory store
    redis = None  # type: ignore


class OnlineFeatureStore:
    """Minimal online feature cache with optional Redis backing."""

    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 120) -> None:
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, float]] = {}
        self._client = None
        if redis_url and redis is not None:
            try:
                self._client = redis.Redis.from_url(redis_url, decode_responses=True)  # type: ignore[attr-defined]
            except Exception:
                self._client = None

    def _serialize(self, features: Dict[str, float]) -> str:
        return ";".join(f"{k}:{v}" for k, v in sorted(features.items()))

    def _deserialize(self, payload: str) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for item in payload.split(";"):
            if not item:
                continue
            key, _, value = item.partition(":")
            try:
                result[key] = float(value)
            except ValueError:
                continue
        return result

    def set(self, symbol: str, features: Dict[str, float]) -> None:
        features["updated_ts"] = time.time()
        self._cache[symbol] = features
        if self._client is not None:
            self._client.setex(symbol, self.ttl_seconds, self._serialize(features))  # type: ignore[call-arg]

    def get(self, symbol: str) -> Dict[str, float]:
        data = self._cache.get(symbol)
        if data and time.time() - data.get("updated_ts", 0.0) < self.ttl_seconds:
            return dict(data)
        if self._client is not None:
            payload = self._client.get(symbol)
            if payload:
                decoded = self._deserialize(payload)
                decoded["from_redis"] = 1.0
                self._cache[symbol] = decoded
                return decoded
        return {}
