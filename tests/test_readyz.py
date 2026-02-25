from __future__ import annotations

import asyncio

from fastapi import Request

import gateway
from routers.core import readyz


def _make_request() -> Request:
    request = Request()
    request.app = gateway.app
    return request


def test_readyz() -> None:
    payload = asyncio.run(readyz(_make_request()))
    assert payload["db"] is True
    assert payload["registry"] is True
    assert payload["agents"] is True
    assert payload["ready"] is True
