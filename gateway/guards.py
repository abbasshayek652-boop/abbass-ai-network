from __future__ import annotations

import time
from collections import deque
from typing import Deque, Tuple

from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: object) -> str:
    user = getattr(getattr(request, "state", object()), "user_id", None)
    if user:
        return str(user)
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)


class IdempotencyCache:
    def __init__(self, ttl_seconds: int = 5) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, float] = {}

    def _purge(self, now: float) -> None:
        expired = [key for key, ts in self._store.items() if now - ts >= self.ttl_seconds]
        for key in expired:
            self._store.pop(key, None)

    def allow(self, key: str) -> bool:
        now = time.time()
        self._purge(now)
        ts = self._store.get(key)
        if ts and now - ts < self.ttl_seconds:
            return False
        self._store[key] = now
        return True


class CircuitBreaker:
    def __init__(self, threshold: int = 5, window_seconds: int = 300, cooldown_seconds: int = 120) -> None:
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._errors: Deque[float] = deque()
        self._opened_at: float | None = None
        self._reason: str | None = None

    def _purge(self, now: float) -> None:
        while self._errors and now - self._errors[0] > self.window_seconds:
            self._errors.popleft()

    def allow(self) -> bool:
        now = time.time()
        if self._opened_at is None:
            return True
        if now - self._opened_at >= self.cooldown_seconds:
            self._opened_at = None
            self._reason = None
            self._errors.clear()
            return True
        return False

    def record_success(self) -> None:
        if self.allow():
            self._errors.clear()
            self._opened_at = None
            self._reason = None

    def record_error(self, reason: str) -> None:
        now = time.time()
        self._purge(now)
        self._errors.append(now)
        if len(self._errors) >= self.threshold and self._opened_at is None:
            self._opened_at = now
            self._reason = reason

    def state(self) -> dict[str, object]:
        open_state = self._opened_at is not None and not self.allow()
        cooldown = 0.0
        if self._opened_at is not None:
            cooldown = max(0.0, self.cooldown_seconds - (time.time() - self._opened_at))
        return {
            "open": open_state,
            "reason": self._reason,
            "cooldown_seconds": cooldown,
            "errors_last_window": len(self._errors),
        }


idempotency_cache = IdempotencyCache()
circuit_breaker = CircuitBreaker()
