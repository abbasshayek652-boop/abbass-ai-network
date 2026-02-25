from __future__ import annotations

import asyncio

from fastapi import Request

import gateway
from gateway_pkg.auth import AuthContext
from routers.agents import agent_detail, list_agents


def _make_request() -> Request:
    request = Request()
    request.app = gateway.app
    return request


def test_agents_list_and_detail() -> None:
    ctx = AuthContext(user_id="tester", role="viewer")
    payload = asyncio.run(list_agents(_make_request(), ctx))
    assert "agents" in payload
    assert any(agent["key"] == "learning" for agent in payload["agents"])

    detail = asyncio.run(agent_detail("learning", _make_request(), ctx))
    assert detail["agent"]["key"] == "learning"
