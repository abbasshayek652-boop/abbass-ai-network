from __future__ import annotations

import asyncio

from routers.core import healthz


def test_healthz() -> None:
    payload = asyncio.run(healthz())
    assert payload["ok"] is True
    assert payload["service"] == "mother_ai"
    assert "timestamp" in payload
