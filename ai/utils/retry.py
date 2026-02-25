from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Iterable, Tuple, Type, TypeVar

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    exceptions: Iterable[Type[BaseException]] = (Exception,),
) -> T:
    """Retry an async callable with exponential backoff."""
    exc_tuple: Tuple[Type[BaseException], ...] = tuple(exceptions)
    for attempt in range(attempts):
        try:
            return await fn()
        except exc_tuple:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(base_delay * (2**attempt))
    raise RuntimeError("Retry loop exited unexpectedly")

