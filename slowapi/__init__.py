from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable


class RateLimitExceeded(Exception):
    status_code = 429


class Limiter:
    def __init__(self, key_func: Callable[[Any], str]) -> None:
        self.key_func = key_func
        self._store: dict[tuple[str, str], list[float]] = {}

    def _parse_rule(self, rule: str) -> tuple[int, float]:
        count_str, window = rule.split("/")
        count = int(count_str)
        if window.startswith("minute"):
            seconds = 60.0
        elif window.startswith("second"):
            seconds = 1.0
        else:
            seconds = 60.0
        return count, seconds

    def limit(self, rule: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
        count, window = self._parse_rule(rule)

        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                request = None
                if len(args) > 1:
                    request = args[1]
                elif "request" in kwargs:
                    request = kwargs["request"]
                key = self.key_func(request) if request is not None else "default"
                bucket_key = (key, func.__name__)
                now = time.time()
                timestamps = self._store.setdefault(bucket_key, [])
                self._store[bucket_key] = [ts for ts in timestamps if now - ts < window]
                if len(self._store[bucket_key]) > count:
                    raise RateLimitExceeded()
                self._store[bucket_key].append(now)
                return await func(*args, **kwargs)

            return wrapper

        return decorator


class SlowAPIMiddleware:  # pragma: no cover - stub
    def __init__(self, app: Any, limiter: Limiter) -> None:
        self.app = app
        self.limiter = limiter
