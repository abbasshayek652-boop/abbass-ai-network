from __future__ import annotations

import asyncio

from fastapi import Request

import gateway
from gateway.auth import AuthContext
from routers.core import status_endpoint


def _make_request() -> Request:
    request = Request()
    request.app = gateway.app
    return request


def test_status() -> None:
    ctx = AuthContext(user_id="tester", role="viewer")
    payload = asyncio.run(status_endpoint(_make_request(), ctx))
    assert "loaded_agents" in payload
    assert "running" in payload
    assert isinstance(payload["loaded_agents"], list)
    assert isinstance(payload["running"], dict)
