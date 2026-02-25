from __future__ import annotations

import uuid

from ai.utils.logging import CORRELATION_ID


class CorrelationIdMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):  # pragma: no cover - stub behaviour
        correlation_id = scope.get("headers", [])
        cid = None
        for name, value in correlation_id:
            if name.lower() == b"x-correlation-id":
                cid = value.decode()
                break
        cid = cid or str(uuid.uuid4())
        token = CORRELATION_ID.set(cid)
        scope.setdefault("state", {})["correlation_id"] = cid
        try:
            await self.app(scope, receive, send)
        finally:
            CORRELATION_ID.reset(token)
