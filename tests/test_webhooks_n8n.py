from __future__ import annotations

import asyncio

from fastapi import Request

import gateway
from ai.settings import settings
from routers.control import N8nWebhook, n8n_webhook


def _make_request() -> Request:
    request = Request()
    request.app = gateway.app
    return request


def test_n8n_webhook_token_enforced() -> None:
    settings.webhook_token = "secret-token"
    payload = N8nWebhook(action="status", agent_key="learning", meta={})
    try:
        asyncio.run(n8n_webhook(payload, _make_request(), x_webhook_token="bad-token"))
    except Exception as exc:  # noqa: BLE001
        assert getattr(exc, "status_code", None) == 401
    else:
        raise AssertionError("Expected invalid token to fail")
