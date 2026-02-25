from __future__ import annotations

import logging
import sys
from contextvars import ContextVar


CORRELATION_ID: ContextVar[str] = ContextVar("correlation_id", default="-")


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        record.correlation_id = CORRELATION_ID.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging once for the application."""
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_CorrelationFilter())
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [cid=%(correlation_id)s] %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level.upper())

