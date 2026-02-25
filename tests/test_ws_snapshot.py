from __future__ import annotations

import asyncio

import gateway
from dashboard import ws as dashboard_ws


def test_websocket_snapshot_provider() -> None:
    async def runner() -> None:
        assert dashboard_ws._SNAPSHOT_PROVIDER is not None
        payload = await dashboard_ws._SNAPSHOT_PROVIDER()
        assert "agents" in payload
        assert "circuit_breaker" in payload
        assert payload["circuit_breaker"].keys() >= {"open", "reason", "cooldown_seconds"}

    asyncio.run(runner())
