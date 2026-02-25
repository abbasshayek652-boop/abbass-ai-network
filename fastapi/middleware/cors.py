from __future__ import annotations

from typing import Any


class CORSMiddleware:  # pragma: no cover - stub
    def __init__(self, app: Any, **kwargs: Any) -> None:
        self.app = app
        self.kwargs = kwargs
