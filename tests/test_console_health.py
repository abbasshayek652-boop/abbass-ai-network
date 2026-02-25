from __future__ import annotations

import asyncio

from fastapi import Request

import gateway
from routers.console import console_health


def _make_request() -> Request:
    request = Request()
    request.app = gateway.app
    return request


def test_console_health() -> None:
    payload = asyncio.run(console_health(_make_request()))
    assert "health" in payload
    assert "ready" in payload
    assert "version" in payload
    assert payload["health"]["ok"] is True
